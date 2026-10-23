// Diagnose and, where possible, recover entry points that ExportDQXI could not create.
// Usage: -postScript DiagnoseMissing.java <projectRoot> <outputJsonl>
//@category DQXI

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.lang.Register;
import ghidra.program.model.lang.RegisterValue;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

public class DiagnoseMissing extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: DiagnoseMissing.java <projectRoot> <outputJsonl>");
            return;
        }
        File root = new File(args[0]);
        File outFile = new File(args[1]);
        File index = new File(root, "decomp/ghidra/functions.jsonl");
        if (!index.isFile()) {
            println("missing " + index);
            return;
        }
        List<String> missing = new ArrayList<>();
        List<String> modes = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(index))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (line.contains("\"status\":\"missing_function\"")) {
                    String a = field(line, "address");
                    String m = field(line, "mode");
                    if (a != null) {
                        missing.add(a);
                        modes.add(m == null ? "arm" : m);
                    }
                }
            }
        }
        println("missing=" + missing.size());
        Register tmode = currentProgram.getProgramContext().getRegister("TMode");
        RegisterValue thumb = tmode == null ? null : new RegisterValue(tmode, BigInteger.ONE);
        FunctionManager fm = currentProgram.getFunctionManager();

        DecompInterface decomp = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        decomp.setOptions(opts);
        decomp.toggleCCode(true);
        decomp.openProgram(currentProgram);
        File outDir = new File(root, "decomp/ghidra/recovered");
        outDir.mkdirs();

        try (PrintWriter out = new PrintWriter(new FileWriter(outFile))) {
            int covered = 0, created = 0, failed = 0;
            for (int i = 0; i < missing.size(); i++) {
                if (monitor.isCancelled()) break;
                Address start = toAddr(missing.get(i));
                Function containing = fm.getFunctionContaining(start);
                if (containing != null && !containing.getEntryPoint().equals(start)) {
                    covered++;
                    out.println(String.format(
                        "{\"address\":\"%s\",\"status\":\"covered_by\",\"container\":%s,\"container_entry\":\"%s\"}",
                        start, quote(containing.getName()), containing.getEntryPoint()));
                    continue;
                }
                Function f = fm.getFunctionAt(start);
                if (f == null) {
                    if ("thumb".equalsIgnoreCase(modes.get(i)) && thumb != null) {
                        AddressSet one = new AddressSet(start, start.add(1));
                        DisassembleCommand cmd = new DisassembleCommand(one, null, true);
                        cmd.setInitialContext(thumb);
                        cmd.applyTo(currentProgram, monitor);
                    } else {
                        disassemble(start);
                    }
                    f = createFunction(start, null);
                }
                if (f == null) {
                    failed++;
                    out.println(String.format("{\"address\":\"%s\",\"status\":\"unrecovered\"}", start));
                    continue;
                }
                String c = null;
                try {
                    DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                    if (res != null && res.decompileCompleted() && res.getDecompiledFunction() != null) {
                        c = res.getDecompiledFunction().getC();
                    }
                } catch (Exception ignored) {
                }
                if (c == null) {
                    failed++;
                    out.println(String.format("{\"address\":\"%s\",\"status\":\"created_no_decompile\"}", start));
                } else {
                    created++;
                    File fnOut = new File(outDir, f.getName() + "_" + start.toString().replace("0x", "") + ".c");
                    try (PrintWriter pw = new PrintWriter(new FileWriter(fnOut))) {
                        pw.println("/* Recovered entry point " + start + " (" + modes.get(i) + ") */");
                        pw.println(c);
                    }
                    out.println(String.format(
                        "{\"address\":\"%s\",\"status\":\"recovered\",\"name\":%s,\"file\":\"recovered/%s\"}",
                        start, quote(f.getName()), fnOut.getName()));
                }
            }
            println("covered=" + covered + " recovered=" + created + " failed=" + failed);
        }
        decomp.dispose();
    }

    private static String field(String json, String key) {
        String needle = "\"" + key + "\":\"";
        int a = json.indexOf(needle);
        if (a < 0) return null;
        a += needle.length();
        int b = json.indexOf('"', a);
        return b > a ? json.substring(a, b) : null;
    }

    private static String quote(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
}
