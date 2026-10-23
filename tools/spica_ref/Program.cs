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

if (args.Length < 3 || (args[0] != "textures" && args[0] != "skin" && args[0] != "materials" && args[0] != "obj" && args[0] != "matanims"))
{
    Console.Error.WriteLine("usage: SpicaRef textures|materials|skin <list.txt> <out> [root]");
    return 2;
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
