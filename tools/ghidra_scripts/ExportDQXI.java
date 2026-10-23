// Export high-level C from a DQXI ARMv6 Ghidra project.
// Usage: -postScript ExportDQXI.java <projectRoot> <outputDir> [maxFunctions]
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
import ghidra.program.model.listing.Listing;

public class ExportDQXI extends GhidraScript {

    private static class Seed {
        Address start;
        Address end;
        String mode;
        String name;
        long size;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: ExportDQXI.java <projectRoot> <outputDir> [maxFunctions]");
            return;
        }
        File root = new File(args[0]);
        File outDir = new File(args[1]);
        int limit = args.length > 2 ? Integer.parseInt(args[2]) : Integer.MAX_VALUE;
        File seedFile = new File(root, "decomp/function_seed.tsv");
        if (!seedFile.isFile()) {
            println("missing seed: " + seedFile);
            return;
        }
        outDir.mkdirs();
        File fnDir = new File(outDir, "functions");
        fnDir.mkdirs();

        List<Seed> seeds = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(seedFile))) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                String[] p = line.split("\t");
                if (p.length < 4) continue;
                Seed s = new Seed();
                s.start = toAddr(p[0]);
                s.mode = p[1];
                s.name = p[2];
                s.size = Long.parseLong(p[3]);
                s.end = s.start.add(Math.max(1, s.size) - 1);
                seeds.add(s);
            }
        }
        if (seeds.size() > limit) seeds = seeds.subList(0, limit);
        println("seeds=" + seeds.size());

        Register tmode = currentProgram.getProgramContext().getRegister("TMode");
        RegisterValue thumb = tmode == null ? null : new RegisterValue(tmode, BigInteger.ONE);
        RegisterValue arm = tmode == null ? null : new RegisterValue(tmode, BigInteger.ZERO);

        // Make sure every discovered entry point is a function in the expected mode.
        int made = 0;
        for (Seed s : seeds) {
            if (monitor.isCancelled()) break;
            Listing listing = currentProgram.getListing();
            AddressSet range = new AddressSet(s.start, s.end);
            if ("thumb".equalsIgnoreCase(s.mode) && thumb != null) {
                // Auto-analysis may have decoded these bytes as ARM. Clear only this
                // small function range, then disassemble with TMode=1.
                clearListing(s.start, s.end);
                DisassembleCommand cmd = new DisassembleCommand(range, null, true);
                cmd.setInitialContext(thumb);
                cmd.applyTo(currentProgram, monitor);
            } else if (arm != null) {
                if (listing.getInstructionAt(s.start) == null) {
                    disassemble(s.start);
                }
            }
            Function f = getFunctionAt(s.start);
            if (f == null) {
                f = createFunction(s.start, s.name);
                made++;
            }
            if (f != null && !f.getName().equals(s.name)) {
                try {
                    f.setName(s.name, ghidra.program.model.symbol.SourceType.USER_DEFINED);
                } catch (Exception ignored) {
                }
            }
        }
        println("created missing functions=" + made);

        DecompInterface decomp = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        decomp.setOptions(opts);
        decomp.toggleCCode(true);
        decomp.toggleSyntaxTree(true);
        decomp.setSimplificationStyle("decompile");
        if (!decomp.openProgram(currentProgram)) {
            println("decompiler open failed: " + decomp.getLastMessage());
            return;
        }

        PrintWriter index = new PrintWriter(new FileWriter(new File(outDir, "functions.jsonl")));
        int ok = 0, failed = 0, missing = 0;
        long started = System.currentTimeMillis();
        for (Seed s : seeds) {
            if (monitor.isCancelled()) break;
            Function f = getFunctionAt(s.start);
            if (f == null) {
                missing++;
                index.println(String.format("{\"address\":\"%s\",\"name\":\"%s\",\"mode\":\"%s\",\"status\":\"missing_function\"}",
                        s.start, s.name, s.mode));
                continue;
            }
            String c = null;
            String signature = "";
            try {
                DecompileResults res = decomp.decompileFunction(f, 120, monitor);
                if (res != null && res.decompileCompleted() && res.getDecompiledFunction() != null) {
                    c = res.getDecompiledFunction().getC();
                    signature = res.getDecompiledFunction().getSignature();
                } else if (res != null) {
                    c = "/* decompile failed: " + res.getErrorMessage() + " */\n";
                }
            } catch (Exception e) {
                c = "/* decompile exception: " + e.getMessage() + " */\n";
            }
            String base = String.format("%s_%s", s.name, s.start.toString().replace("0x", ""));
            File out = new File(fnDir, base + ".c");
            if (c == null) {
                failed++;
                index.println(String.format("{\"address\":\"%s\",\"name\":\"%s\",\"mode\":\"%s\",\"status\":\"failed\",\"file\":\"%s\"}",
                        s.start, s.name, s.mode, out.getName()));
            } else {
                ok++;
                try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
                    pw.println("/*");
                    pw.println(" * DQXI 3DS native function");
                    pw.println(" * Address: " + s.start + " (" + s.mode + ")");
                    pw.println(" * Symbol:  " + s.name);
                    if (!signature.isEmpty()) pw.println(" * Signature: " + signature.replace("\n", " "));
                    pw.println(" * Regenerated by Ghidra from the retail executable.");
                    pw.println(" */");
                    pw.println(c);
                }
                index.println(String.format("{\"address\":\"%s\",\"name\":\"%s\",\"mode\":\"%s\",\"size\":%d,\"status\":\"ok\",\"signature\":%s,\"file\":\"functions/%s\"}",
                        s.start, s.name, s.mode, s.size, jsonString(signature), out.getName()));
            }
            if ((ok + failed + missing) % 250 == 0) {
                long dt = Math.max(1, System.currentTimeMillis() - started);
                println(String.format("progress %d/%d ok=%d failed=%d missing=%d (%.1f fn/s)",
                        ok + failed + missing, seeds.size(), ok, failed, missing,
                        (ok + failed + missing) * 1000.0 / dt));
            }
        }
        index.close();
        decomp.dispose();
        println(String.format("DONE ok=%d failed=%d missing=%d output=%s", ok, failed, missing, outDir));
    }

    private static String jsonString(String s) {
        if (s == null) return "null";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }
}
