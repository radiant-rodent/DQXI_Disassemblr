// SPICA reference dumper used by the model exporter and its audits.
//
//   SpicaRef textures  <list.txt> <out_dir> [root]
//   SpicaRef materials <list.txt> <out.json> [root]
//   SpicaRef skin      <list.txt> <out.json> [root]
//   SpicaRef obj       <file.bch> <out.obj>
//   SpicaRef matanims  <file.bch> <out.json>
//
// Every per-draw entry carries "vbo"/"ibo": the file offsets of the draw's
// vertex and index buffers. tools/model_tool.py matches draws on that pair, so
// the manifests stay correct even where SPICA's model -> mesh -> submesh order
// differs from the order of draws in the command stream.
//
// `materials` writes the material and texture names of every draw
// (game_assets/models/material_map.json.gz).
//
// `skin` writes, per BCH and per draw (model -> mesh -> submesh, the same order
// as material_map.json.gz), how a rigid/unskinned draw is placed by its bones:
// the world matrix of every bone in the submesh palette (12 floats, row-vector
// System.Numerics layout M11..M43) and the fixed BoneIndex when the vertex
// buffer has no BoneIndex attribute. Smooth-skinned draws are already stored in
// model space and are written as null. Files whose draws all need no transform
// are omitted.
//
// `textures`: for every BCH path in list.txt, writes each embedded texture as
// <out_dir>/<rel path without .bch>/<texture>.png (stored row order, the same
// convention as tools/texture_tool.decode_tiled) plus an index.json with the
// SPICA-reported width/height/format of every texture.
using System.Text.Json;
using SPICA.Formats.CtrH3D;
using SixLabors.ImageSharp;

// text output (OBJ) must use '.' decimals whatever the machine locale is
System.Globalization.CultureInfo.DefaultThreadCurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
System.Globalization.CultureInfo.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;

if (args.Length < 3 || (args[0] == "rig" && args.Length < 4) || (args[0] != "textures" && args[0] != "skin" && args[0] != "materials" && args[0] != "obj" && args[0] != "matanims" && args[0] != "rig"))
{
    Console.Error.WriteLine("usage: SpicaRef textures|materials|skin <list.txt> <out> [root]");
    return 2;
}
if (args[0] == "rig")
{
    return DumpRig(args[1], args[2], Path.GetFullPath(args[3]));
}
if (args[0] == "matanims")
{
    return DumpMaterialAnims(args[1], Path.GetFullPath(args[2]));
}
if (args[0] == "obj")
{
    return DumpObj(args[1], Path.GetFullPath(args[2]));
}
if (args[0] == "materials")
{
    return DumpMaterials(args[1], Path.GetFullPath(args[2]), Path.GetFullPath(args.Length > 3 ? args[3] : "."));
}
if (args[0] == "skin")
{
    return DumpSkin(args[1], Path.GetFullPath(args[2]), Path.GetFullPath(args.Length > 3 ? args[3] : "."));
}
var listPath = args[1];
var outDir = Path.GetFullPath(args[2]);
var root = Path.GetFullPath(args.Length > 3 ? args[3] : ".");
var index = new Dictionary<string, List<Dictionary<string, object>>>();
int ok = 0, fail = 0;
foreach (var raw in File.ReadLines(listPath))
{
    var path = raw.Trim();
    if (path.Length == 0 || !File.Exists(path)) continue;
    var rel = Path.GetRelativePath(root, Path.GetFullPath(path)).Replace(Path.DirectorySeparatorChar, '/');
    try
    {
        var h3d = H3D.Open(File.ReadAllBytes(path));
        var dir = Path.Combine(outDir, rel[..^4]);
        var list = new List<Dictionary<string, object>>();
        foreach (var t in h3d.Textures)
        {
            Directory.CreateDirectory(dir);
            t.ToBitmap().SaveAsPng(Path.Combine(dir, t.Name + ".png"));
            list.Add(new Dictionary<string, object>
            {
                ["name"] = t.Name,
                ["width"] = t.Width,
                ["height"] = t.Height,
                ["format"] = t.Format.ToString(),
                ["cube"] = t.IsCubeTexture,
            });
        }
        index[rel] = list;
        ok++;
    }
    catch (Exception e)
    {
        Console.Error.WriteLine($"{rel}: {e.Message}");
        fail++;
    }
}
File.WriteAllText(Path.Combine(outDir, "index.json"), JsonSerializer.Serialize(index));
Console.WriteLine($"{ok} BCH ok, {fail} failed -> {outDir}");
return 0;

static int DumpSkin(string listPath, string outPath, string root)
{
    var result = new Dictionary<string, List<Dictionary<string, object>?>>();
    int ok = 0, fail = 0;
    foreach (var raw in File.ReadLines(listPath))
    {
        var path = raw.Trim();
        if (path.Length == 0 || !File.Exists(path)) continue;
        var rel = Path.GetRelativePath(root, Path.GetFullPath(path)).Replace(Path.DirectorySeparatorChar, '/');
        try
        {
            var h3d = H3D.Open(File.ReadAllBytes(path));
            var draws = new List<Dictionary<string, object>?>();
            bool any = false;
            foreach (var model in h3d.Models)
            {
                var skel = model.Skeleton;
                foreach (var mesh in model.Meshes)
                {
                    int? fixedBone = null;
                    foreach (var fa in mesh.FixedAttributes)
                        if (fa.Name == SPICA.PICA.Commands.PICAAttributeName.BoneIndex) fixedBone = (int)fa.Value.X;
                    foreach (var sm in mesh.SubMeshes)
                    {
                        if (skel == null || skel.Count == 0 || sm.Skinning == SPICA.Formats.CtrH3D.Model.Mesh.H3DSubMeshSkinning.Smooth)
                        {
                            // already in model space: no palette
                            draws.Add(new Dictionary<string, object>
                            {
                                ["skinning"] = sm.Skinning.ToString(),
                                ["indices"] = sm.Indices.Length,
                                ["vbo"] = mesh.BufferAddress,
                                ["ibo"] = sm.IndexBufferAddress,
                            });
                            continue;
                        }
                        var palette = new List<float[]>();
                        for (int i = 0; i < sm.BoneIndicesCount; i++)
                        {
                            int b = sm.BoneIndices[i];
                            var m = b < skel.Count ? skel[b].GetWorldTransform(skel) : System.Numerics.Matrix4x4.Identity;
                            palette.Add(new[] { m.M11, m.M12, m.M13, m.M21, m.M22, m.M23, m.M31, m.M32, m.M33, m.M41, m.M42, m.M43 });
                            if (!m.IsIdentity) any = true;
                        }
                        var d = new Dictionary<string, object>
                        {
                            ["skinning"] = sm.Skinning.ToString(),
                            ["indices"] = sm.Indices.Length,
                            ["vbo"] = mesh.BufferAddress,
                            ["ibo"] = sm.IndexBufferAddress,
                            ["palette"] = palette,
                        };
                        if (fixedBone.HasValue) d["fixed_bone"] = fixedBone.Value;
                        draws.Add(d);
                    }
                }
            }
            if (any) result[rel] = draws;
            ok++;
        }
        catch (Exception e)
        {
            Console.Error.WriteLine($"{rel}: {e.Message}");
            fail++;
        }
    }
    File.WriteAllText(outPath, JsonSerializer.Serialize(result));
    Console.WriteLine($"{ok} BCH ok, {fail} failed, {result.Count} need bone placement -> {outPath}");
    return 0;
}

static int DumpMaterials(string listPath, string outPath, string root)
{
    var entries = new Dictionary<string, List<Dictionary<string, object?>>>();
    int ok = 0, fail = 0;
    foreach (var raw in File.ReadLines(listPath))
    {
        var path = raw.Trim();
        if (path.Length == 0 || !File.Exists(path)) continue;
        var rel = Path.GetRelativePath(root, Path.GetFullPath(path)).Replace(Path.DirectorySeparatorChar, '/');
        try
        {
            var h3d = H3D.Open(File.ReadAllBytes(path));
            var list = new List<Dictionary<string, object?>>();
            foreach (var model in h3d.Models)
            {
                foreach (var mesh in model.Meshes)
                {
                    var mat = mesh.MaterialIndex < model.Materials.Count ? model.Materials[mesh.MaterialIndex] : null;
                    for (int s = 0; s < mesh.SubMeshes.Count; s++)
                    {
                        list.Add(new Dictionary<string, object?>
                        {
                            ["model"] = model.Name,
                            ["mesh"] = list.Count,
                            ["submesh"] = s,
                            ["material"] = mesh.MaterialIndex,
                            ["material_name"] = mat?.Name ?? "",
                            ["tex0"] = mat?.Texture0Name ?? "",
                            ["tex1"] = mat?.Texture1Name ?? "",
                            ["tex2"] = mat?.Texture2Name ?? "",
                            ["vbo"] = mesh.BufferAddress,
                            ["ibo"] = mesh.SubMeshes[s].IndexBufferAddress,
                            ["texcoord_config"] = mat?.MaterialParams.TexCoordConfig.ToString() ?? "",
                            // first two colour combiner stages, e.g. "Add(Texture0,Texture1,Constant)"
                            ["tev"] = mat == null ? Array.Empty<string>() : mat.MaterialParams.TexEnvStages.Take(2)
                                .Select(st => $"{st.Combiner.Color}({string.Join(",", st.Source.Color)})").ToArray(),
                            // alpha path of every stage, e.g. "Modulate(Texture0,PrimaryColor,..)"
                            ["tev_alpha"] = mat == null ? Array.Empty<string>() : mat.MaterialParams.TexEnvStages
                                .Select(st => $"{st.Combiner.Alpha}({string.Join(",", st.Source.Alpha)})").ToArray(),
                            // alpha inputs with the channel each reads, e.g. "Texture1:Red"
                            ["tev_alpha_ops"] = mat == null ? Array.Empty<string>() : mat.MaterialParams.TexEnvStages.Take(2)
                                .Select(st => $"{st.Combiner.Alpha}(" + string.Join(",", st.Source.Alpha.Zip(st.Operand.Alpha, (src, op) => $"{src}:{op}")) + ")").ToArray(),
                            ["tev_color_ops"] = mat == null ? Array.Empty<string>() : mat.MaterialParams.TexEnvStages.Take(2)
                                .Select(st => $"{st.Combiner.Color}(" + string.Join(",", st.Source.Color.Zip(st.Operand.Color, (src, op) => $"{src}:{op}")) + ")").ToArray(),
                            // colour scale per stage (One/Two/Four), e.g. vertex lighting x2
                            ["tev_scale"] = mat == null ? Array.Empty<string>() : mat.MaterialParams.TexEnvStages.Take(2)
                                .Select(st => st.Scale.Color.ToString()).ToArray(),
                            ["blend_mode"] = mat?.MaterialParams.ColorOperation.BlendMode.ToString() ?? "",
                            ["blend"] = mat == null ? "" : $"{mat.MaterialParams.BlendFunction.ColorSrcFunc},{mat.MaterialParams.BlendFunction.ColorDstFunc}",
                            ["alpha_test"] = mat == null || !mat.MaterialParams.AlphaTest.Enabled ? "" :
                                $"{mat.MaterialParams.AlphaTest.Function},{mat.MaterialParams.AlphaTest.Reference}",
                            ["depth_write"] = mat?.MaterialParams.DepthColorMask.DepthWrite ?? true,
                            ["layer"] = mat?.MaterialParams.TranslucencyKind.ToString() ?? "",
                            // mesh node (e.g. a hand variant) and whether the game shows it by default
                            ["node"] = mesh.NodeIndex < model.MeshNodesTree.Count ? model.MeshNodesTree.Find(mesh.NodeIndex) : "",
                            ["visible"] = mesh.NodeIndex >= model.MeshNodesVisibility.Count || model.MeshNodesVisibility[mesh.NodeIndex],
                            ["priority"] = mesh.Priority,
                            // per-unit texture-coordinate transform the GPU applies before sampling
                            ["uv_coords"] = mat == null ? Array.Empty<Dictionary<string, object>>() : mat.MaterialParams.TextureCoords
                                .Select(tc => new Dictionary<string, object>
                                {
                                    ["scale"] = new[] { tc.Scale.X, tc.Scale.Y },
                                    ["rotation"] = tc.Rotation,
                                    ["translation"] = new[] { tc.Translation.X, tc.Translation.Y },
                                    ["type"] = tc.TransformType.ToString(),
                                    ["mapping"] = tc.MappingType.ToString(),
                                }).ToArray(),
                        });
                    }
                }
            }
            entries[rel] = list;
            ok++;
        }
        catch (Exception e)
        {
            Console.Error.WriteLine($"{rel}: {e.Message}");
            fail++;
        }
    }
    File.WriteAllText(outPath, JsonSerializer.Serialize(entries));
    Console.WriteLine($"{ok} BCH ok, {fail} failed -> {outPath}");
    return 0;
}

// `obj`: SPICA's own placement of one BCH as a reference OBJ (world-space
// vertices via MeshTransform, UVs through the material texture transform),
// plus <out>.materials.json with every material's texture-coordinate settings.
static int DumpObj(string bchPath, string outPath)
{
    var h3d = H3D.Open(File.ReadAllBytes(bchPath));
    var obj = new System.Text.StringBuilder();
    var mtl = new System.Text.StringBuilder();
    var mats = new List<Dictionary<string, object>>();
    obj.AppendLine($"mtllib {Path.GetFileNameWithoutExtension(outPath)}.mtl");
    int baseIndex = 1;
    foreach (var model in h3d.Models)
    {
        for (int mi = 0; mi < model.Materials.Count; mi++)
        {
            var m = model.Materials[mi];
            var units = new List<Dictionary<string, object>>();
            var names = new[] { m.Texture0Name, m.Texture1Name, m.Texture2Name };
            for (int u = 0; u < 3; u++)
            {
                var tc = m.MaterialParams.TextureCoords[u];
                units.Add(new Dictionary<string, object>
                {
                    ["texture"] = names[u] ?? "",
                    ["scale"] = new[] { tc.Scale.X, tc.Scale.Y }, ["rotation"] = tc.Rotation,
                    ["translation"] = new[] { tc.Translation.X, tc.Translation.Y },
                    ["transform_type"] = tc.TransformType.ToString(), ["mapping"] = tc.MappingType.ToString(),
                    ["uv_source"] = tc.ReferenceCameraIndex,
                });
            }
            mats.Add(new Dictionary<string, object>
            {
                ["name"] = m.Name, ["tex0"] = m.Texture0Name ?? "",
                ["texcoord_config"] = m.MaterialParams.TexCoordConfig.ToString(),
                ["units"] = units,
                ["tev"] = m.MaterialParams.TexEnvStages.Select(st => new Dictionary<string, object>
                {
                    ["color_src"] = st.Source.Color.Select(x => x.ToString()).ToArray(),
                    ["color_op"] = st.Operand.Color.Select(x => x.ToString()).ToArray(),
                    ["color_combiner"] = st.Combiner.Color.ToString(),
                    ["alpha_src"] = st.Source.Alpha.Select(x => x.ToString()).ToArray(),
                    ["alpha_op"] = st.Operand.Alpha.Select(x => x.ToString()).ToArray(),
                    ["alpha_combiner"] = st.Combiner.Alpha.ToString(),
                    ["constant"] = new[] { st.Color.R, st.Color.G, st.Color.B, st.Color.A },
                }).ToArray(),
            });
            mtl.AppendLine($"newmtl mat{mi}\nKd 1 1 1\nmap_Kd {m.Texture0Name}.png\n");
        }
        int meshIndex = 0;
        foreach (var mesh in model.Meshes)
        {
            var verts = SPICA.Formats.Common.MeshTransform.GetWorldSpaceVertices(model.Skeleton, mesh);
            var t = model.Materials[mesh.MaterialIndex].MaterialParams.TextureCoords[0].GetTransform();
            foreach (var v in verts)
            {
                obj.AppendLine($"v {v.Position.X} {v.Position.Y} {v.Position.Z}");
                float u = v.TexCoord0.X, w = v.TexCoord0.Y;
                obj.AppendLine($"vt {u * t.M11 + w * t.M21 + t.M41} {u * t.M12 + w * t.M22 + t.M42}");
            }
            obj.AppendLine($"o mesh{meshIndex++}\nusemtl mat{mesh.MaterialIndex}");
            foreach (var sm in mesh.SubMeshes)
                for (int i = 0; i + 2 < sm.Indices.Length; i += 3)
                {
                    int a = sm.Indices[i] + baseIndex, b = sm.Indices[i + 1] + baseIndex, c = sm.Indices[i + 2] + baseIndex;
                    obj.AppendLine($"f {a}/{a} {b}/{b} {c}/{c}");
                }
            baseIndex += verts.Length;
        }
    }
    File.WriteAllText(outPath, obj.ToString());
    File.WriteAllText(Path.ChangeExtension(outPath, ".mtl"), mtl.ToString());
    File.WriteAllText(outPath + ".materials.json", JsonSerializer.Serialize(mats, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"wrote {outPath}");
    return 0;
}

// `matanims`: lists every material animation in one BCH as JSON: animation name,
// frame count, and per element the material, target (e.g. MaterialTexCoord0Trans)
// and the X/Y key frames (frame, value) of 2D vector tracks.
static int DumpMaterialAnims(string bchPath, string outPath)
{
    var h3d = H3D.Open(File.ReadAllBytes(bchPath));
    var anims = new List<Dictionary<string, object>>();
    foreach (var anim in h3d.MaterialAnimations)
    {
        var elements = new List<Dictionary<string, object>>();
        foreach (var e in anim.Elements)
        {
            var d = new Dictionary<string, object> { ["material"] = e.Name, ["target"] = e.TargetType.ToString() };
            if (e.Content is SPICA.Formats.CtrH3D.Animation.H3DAnimVector2D v)
            {
                d["x"] = v.X.KeyFrames.Select(k => new[] { k.Frame, k.Value }).ToArray();
                d["y"] = v.Y.KeyFrames.Select(k => new[] { k.Frame, k.Value }).ToArray();
            }
            elements.Add(d);
        }
        anims.Add(new Dictionary<string, object> { ["name"] = anim.Name, ["frames"] = anim.FramesCount, ["elements"] = elements });
    }
    // mesh-node visibility tracks (hand variants, props): node name -> per-frame bools
    foreach (var anim in h3d.VisibilityAnimations)
    {
        var elements = new List<Dictionary<string, object>>();
        foreach (var e in anim.Elements)
        {
            var d = new Dictionary<string, object> { ["node"] = e.Name, ["target"] = e.TargetType.ToString() };
            if (e.Content is SPICA.Formats.CtrH3D.Animation.H3DAnimBoolean b)
                d["values"] = b.Values.ToArray();
            elements.Add(d);
        }
        anims.Add(new Dictionary<string, object> { ["name"] = anim.Name, ["frames"] = anim.FramesCount, ["kind"] = "visibility", ["elements"] = elements });
    }
    File.WriteAllText(outPath, JsonSerializer.Serialize(anims, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"{anims.Count} material animations -> {outPath}");
    return 0;
}

// `rig`: skeleton + per-vertex skin weights of a model (vertices in the same order
// as `obj`) and every skeletal animation of a motion BCH, sampled once per frame
// as a local bone matrix. Little-endian binary, read by viewer_rs (data/rig.rs):
//   "DQRG" u32 bones { u16 len, name, i16 parent, f32[12] bindLocal, f32[12] bindWorldInverse }
//   u32 vertices { f32[3] bindPos, u8[4] bone, f32[4] weight }
//   u32 anims { u16 len, name, f32 frames, u8 loop, u32 tracks { u16 bone, u32 frames, f32[12] local x frames } }
static void WriteM(BinaryWriter w, System.Numerics.Matrix4x4 m)
{
    w.Write(m.M11); w.Write(m.M12); w.Write(m.M13);
    w.Write(m.M21); w.Write(m.M22); w.Write(m.M23);
    w.Write(m.M31); w.Write(m.M32); w.Write(m.M33);
    w.Write(m.M41); w.Write(m.M42); w.Write(m.M43);
}

static void WriteStr(BinaryWriter w, string text)
{
    var b = System.Text.Encoding.UTF8.GetBytes(text ?? "");
    w.Write((ushort)b.Length); w.Write(b);
}

static System.Numerics.Matrix4x4 Euler(System.Numerics.Vector3 sc, System.Numerics.Vector3 ro, System.Numerics.Vector3 tr)
{
    var m = System.Numerics.Matrix4x4.CreateScale(sc);
    m *= System.Numerics.Matrix4x4.CreateRotationX(ro.X);
    m *= System.Numerics.Matrix4x4.CreateRotationY(ro.Y);
    m *= System.Numerics.Matrix4x4.CreateRotationZ(ro.Z);
    m *= System.Numerics.Matrix4x4.CreateTranslation(tr);
    return m;
}

static int DumpRig(string modelPath, string motionPath, string outPath)
{
    var h3d = H3D.Open(File.ReadAllBytes(modelPath));
    if (h3d.Models.Count == 0) { Console.Error.WriteLine("no model"); return 1; }
    var skel = h3d.Models[0].Skeleton;
    int nb = skel.Count;
    using var fs = File.Create(outPath);
    using var w = new BinaryWriter(fs);
    w.Write(System.Text.Encoding.ASCII.GetBytes("DQRG"));
    w.Write((uint)nb);
    for (int i = 0; i < nb; i++)
    {
        System.Numerics.Matrix4x4.Invert(skel[i].GetWorldTransform(skel), out var inv);
        WriteStr(w, skel[i].Name);
        w.Write((short)skel[i].ParentIndex);
        WriteM(w, skel[i].Transform);
        WriteM(w, inv);
    }
    var verts = new List<(System.Numerics.Vector3 p, byte[] b, float[] wt)>();
    foreach (var m in h3d.Models)
        foreach (var mesh in m.Meshes)
        {
            var wv = SPICA.Formats.Common.MeshTransform.GetWorldSpaceVertices(m.Skeleton, mesh);
            var raw = mesh.GetVertices();
            var info = new (byte[] b, float[] wt)?[wv.Length];
            foreach (var sm in mesh.SubMeshes)
                foreach (ushort idx in sm.Indices)
                {
                    if (info[idx] != null) continue;
                    var v = raw[idx];
                    var bi = new byte[4]; var wt = new float[4];
                    if (sm.Skinning == SPICA.Formats.CtrH3D.Model.Mesh.H3DSubMeshSkinning.Smooth)
                    {
                        for (int k = 0; k < 4; k++)
                        {
                            float wk = v.Weights[k];
                            int bk = v.Indices[k];
                            if (wk > 0 && bk < sm.BoneIndices.Length) { bi[k] = (byte)sm.BoneIndices[bk]; wt[k] = wk; }
                        }
                    }
                    else
                    {
                        bi[0] = (byte)sm.BoneIndices[v.Indices[0]]; wt[0] = 1;
                    }
                    info[idx] = (bi, wt);
                }
            for (int i = 0; i < wv.Length; i++)
            {
                var (bi, wt) = info[i] ?? (new byte[4], new float[] { 1, 0, 0, 0 });
                verts.Add((new System.Numerics.Vector3(wv[i].Position.X, wv[i].Position.Y, wv[i].Position.Z), bi, wt));
            }
        }
    w.Write((uint)verts.Count);
    foreach (var (p, b, wt) in verts)
    {
        w.Write(p.X); w.Write(p.Y); w.Write(p.Z);
        w.Write(b);
        for (int k = 0; k < 4; k++) w.Write(wt[k]);
    }
    var anims = new List<SPICA.Formats.CtrH3D.Animation.H3DAnimation>();
    if (motionPath != "-")
        anims.AddRange(H3D.Open(File.ReadAllBytes(motionPath)).SkeletalAnimations);
    var byName = new Dictionary<string, int>();
    for (int i = 0; i < nb; i++) byName[skel[i].Name] = i;
    w.Write((uint)anims.Count);
    foreach (var anim in anims)
    {
        WriteStr(w, anim.Name);
        w.Write(anim.FramesCount);
        w.Write((byte)((anim.AnimationFlags & SPICA.Formats.CtrH3D.Animation.H3DAnimationFlags.IsLooping) != 0 ? 1 : 0));
        int frames = Math.Max(1, (int)Math.Ceiling(anim.FramesCount) + 1);
        var tracks = new List<(int bone, System.Numerics.Matrix4x4[] m)>();
        foreach (var e in anim.Elements)
        {
            if (!byName.TryGetValue(e.Name, out int bi)) continue;
            var bone = skel[bi];
            var ms = new System.Numerics.Matrix4x4[frames];
            bool ok = true;
            for (int f = 0; f < frames && ok; f++)
            {
                switch (e.Content)
                {
                    case SPICA.Formats.CtrH3D.Animation.H3DAnimTransform t:
                    {
                        var sc = bone.Scale; var ro = bone.Rotation; var tr = bone.Translation;
                        if (t.ScaleExists) sc = new System.Numerics.Vector3(t.ScaleX.GetFrameValue(f), t.ScaleY.GetFrameValue(f), t.ScaleZ.GetFrameValue(f));
                        if (t.RotationExists) ro = new System.Numerics.Vector3(t.RotationX.GetFrameValue(f), t.RotationY.GetFrameValue(f), t.RotationZ.GetFrameValue(f));
                        if (t.TranslationExists) tr = new System.Numerics.Vector3(t.TranslationX.GetFrameValue(f), t.TranslationY.GetFrameValue(f), t.TranslationZ.GetFrameValue(f));
                        ms[f] = Euler(sc, ro, tr); break;
                    }
                    case SPICA.Formats.CtrH3D.Animation.H3DAnimQuatTransform q:
                    {
                        var sc = q.HasScale ? q.GetScaleValue(f) : bone.Scale;
                        var tr = q.HasTranslation ? q.GetTranslationValue(f) : bone.Translation;
                        if (q.HasRotation)
                            ms[f] = System.Numerics.Matrix4x4.CreateScale(sc) * System.Numerics.Matrix4x4.CreateFromQuaternion(q.GetRotationValue(f)) * System.Numerics.Matrix4x4.CreateTranslation(tr);
                        else
                            ms[f] = Euler(sc, bone.Rotation, tr);
                        break;
                    }
                    case SPICA.Formats.CtrH3D.Animation.H3DAnimMtxTransform mt:
                        ms[f] = mt.GetTransform(f).ToMatrix4x4(); break;
                    default:
                        ok = false; break;
                }
            }
            if (ok) tracks.Add((bi, ms));
        }
        w.Write((uint)tracks.Count);
        foreach (var (bi, ms) in tracks)
        {
            w.Write((ushort)bi); w.Write((uint)ms.Length);
            foreach (var m in ms) WriteM(w, m);
        }
    }
    Console.WriteLine($"{nb} bones, {verts.Count} vertices, {anims.Count} animations -> {outPath}");
    return 0;
}
