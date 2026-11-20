// `gltf <model.bch> <out.glb> [anims.txt]`: a rigged binary glTF for Blender.
//
//  - one node per bone (rest TRS, same hierarchy) and a skin over all of them, so Blender builds an armature
//    with the game's joints;
//  - every mesh as a skinned primitive: bind-pose positions, normals, UV0, JOINTS_0/WEIGHTS_0 (Blender turns
//    these into vertex groups = weight paint), and its material's first texture embedded as PNG;
//  - every animation listed in anims.txt (lines "<anim.bch>\t<animation name>", tab-separated; "*" as name = all
//    skeletal animations of that file) as a glTF animation (Blender: one action per clip), posed with the DQXI
//    rules of Compat.Evaluate and stored as per-bone local translation/rotation/scale for every frame at 30 fps.
// Alternate meshes of a part (L_Hand02_MS..) carry extras.dqxi_hidden like tools/model_tool.py's glTF; *_Outline
// shells (expanded in the game's shader, so they would cover the model) are left out unless --outlines.
// tools/export_glb.py picks the animations that work on the rig from game_assets/animations/compat.json.
using System.Numerics;
using System.Text.Json;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Animation;
using SPICA.Formats.CtrH3D.Model;
using SPICA.Formats.CtrH3D.Model.Material;
using SixLabors.ImageSharp;

static class Gltf
{
    sealed class Bin
    {
        public readonly MemoryStream Data = new();
        public readonly List<Dictionary<string, object>> Views = new();
        public readonly List<Dictionary<string, object>> Accessors = new();

        void Align() { while (Data.Length % 4 != 0) Data.WriteByte(0); }

        int View(byte[] bytes, int? target)
        {
            Align();
            var v = new Dictionary<string, object> { ["buffer"] = 0, ["byteOffset"] = (int)Data.Length, ["byteLength"] = bytes.Length };
            if (target.HasValue) v["target"] = target.Value;
            Data.Write(bytes);
            Views.Add(v);
            return Views.Count - 1;
        }

        public int Image(byte[] png) => View(png, null);

        public int Floats(float[] data, int comps, string type, bool minmax = false, int? target = 34962)
        {
            var bytes = new byte[data.Length * 4];
            Buffer.BlockCopy(data, 0, bytes, 0, bytes.Length);
            var a = new Dictionary<string, object> { ["bufferView"] = View(bytes, target), ["componentType"] = 5126, ["count"] = data.Length / comps, ["type"] = type };
            if (minmax)
            {
                var mn = new float[comps]; var mx = new float[comps];
                for (int c = 0; c < comps; c++) { mn[c] = float.MaxValue; mx[c] = float.MinValue; }
                for (int i = 0; i < data.Length; i++) { int c = i % comps; mn[c] = Math.Min(mn[c], data[i]); mx[c] = Math.Max(mx[c], data[i]); }
                a["min"] = mn; a["max"] = mx;
            }
            Accessors.Add(a);
            return Accessors.Count - 1;
        }

        public int UShorts(ushort[] data, int comps, string type, int target)
        {
            var bytes = new byte[data.Length * 2];
            Buffer.BlockCopy(data, 0, bytes, 0, bytes.Length);
            Accessors.Add(new Dictionary<string, object> { ["bufferView"] = View(bytes, target), ["componentType"] = 5123, ["count"] = data.Length / comps, ["type"] = type });
            return Accessors.Count - 1;
        }

        public int UInts(uint[] data)
        {
            var bytes = new byte[data.Length * 4];
            Buffer.BlockCopy(data, 0, bytes, 0, bytes.Length);
            Accessors.Add(new Dictionary<string, object> { ["bufferView"] = View(bytes, 34963), ["componentType"] = 5125, ["count"] = data.Length, ["type"] = "SCALAR" });
            return Accessors.Count - 1;
        }
    }

    static float[] Trs(Matrix4x4 m, out float[] r, out float[] s)
    {
        Matrix4x4.Decompose(m, out var sc, out var q, out var t);
        q = Quaternion.Normalize(q);
        r = new[] { q.X, q.Y, q.Z, q.W };
        s = new[] { sc.X, sc.Y, sc.Z };
        return new[] { t.X, t.Y, t.Z };
    }

    static string? TexName(H3DMaterial m, int u) => u switch { 0 => m.Texture0Name, 1 => m.Texture1Name, 2 => m.Texture2Name, _ => null };

    // The texture unit the colour path samples through real UVs (same rule as tools/model_tool.py
    // _draw_layers): the first texture a colour combiner stage actually reads, skipping environment /
    // projection maps; a UV-mapped "env" texture only when nothing else is sampled. Unit 0 is often a sphere
    // map (ani00001x: Texture0 = env01, the body colour is Texture1).
    static int ColourUnit(H3DMaterial m)
    {
        var mp = m.MaterialParams;
        bool UvMapped(int u) => TexName(m, u) is { Length: > 0 }
            && mp.TextureCoords[u].MappingType == SPICA.Formats.CtrH3D.Model.Material.H3DTextureMappingType.UvCoordinateMap;
        var sampled = new List<int>();
        foreach (var st in mp.TexEnvStages)
        {
            int args = st.Combiner.Color switch
            {
                SPICA.PICA.Commands.PICATextureCombinerMode.Replace => 1,
                SPICA.PICA.Commands.PICATextureCombinerMode.Interpolate or SPICA.PICA.Commands.PICATextureCombinerMode.MultAdd
                    or SPICA.PICA.Commands.PICATextureCombinerMode.AddMult => 3,
                _ => 2,
            };
            for (int k = 0; k < args; k++)
            {
                int u = st.Source.Color[k] switch
                {
                    SPICA.PICA.Commands.PICATextureCombinerSource.Texture0 => 0,
                    SPICA.PICA.Commands.PICATextureCombinerSource.Texture1 => 1,
                    SPICA.PICA.Commands.PICATextureCombinerSource.Texture2 => 2,
                    _ => -1,
                };
                if (u >= 0 && UvMapped(u) && !sampled.Contains(u)) sampled.Add(u);
            }
        }
        var plain = sampled.Where(u => !(TexName(m, u)!.ToLowerInvariant().Contains("env") || TexName(m, u)!.ToLowerInvariant().Contains("cubemap"))).ToList();
        return plain.Count > 0 ? plain[0] : sampled.Count > 0 ? sampled[0] : 0;
    }

    // UV set a unit reads: Config0120 -> unit i uses UV digit i
    static int UvSet(H3DMaterial m, int unit)
    {
        var d = m.MaterialParams.TexCoordConfig.ToString()["Config".Length..];
        return unit < d.Length && char.IsDigit(d[unit]) ? d[unit] - '0' : unit;
    }

    public static int Run(string modelPath, string outPath, string? animList, bool outlines = false)
    {
        var h3d = H3D.Open(File.ReadAllBytes(modelPath));
        if (h3d.Models.Count == 0) { Console.Error.WriteLine("no model"); return 1; }
        var model = h3d.Models[0];
        var skel = model.Skeleton;
        var bones = skel.ToArray();
        int nb = bones.Length;
        var bin = new Bin();
        var nodes = new List<Dictionary<string, object>>();
        var bindWorld = bones.Select(b => b.GetWorldTransform(skel)).ToArray();

        // --- joints
        for (int i = 0; i < nb; i++)
        {
            var t = Trs(bones[i].Transform, out var r, out var s);
            nodes.Add(new Dictionary<string, object> { ["name"] = bones[i].Name, ["translation"] = t, ["rotation"] = r, ["scale"] = s });
        }
        for (int i = 0; i < nb; i++)
        {
            var kids = Enumerable.Range(0, nb).Where(j => bones[j].ParentIndex == i).ToArray();
            if (kids.Length > 0) nodes[i]["children"] = kids;
        }
        var roots = Enumerable.Range(0, nb).Where(i => bones[i].ParentIndex < 0).ToList();
        var ibm = new float[nb * 16];
        for (int i = 0; i < nb; i++)
        {
            Matrix4x4.Invert(bindWorld[i], out var inv);
            // row-vector matrix stored row-major == column-vector matrix stored column-major (glTF)
            var v = new[] { inv.M11, inv.M12, inv.M13, inv.M14, inv.M21, inv.M22, inv.M23, inv.M24, inv.M31, inv.M32, inv.M33, inv.M34, inv.M41, inv.M42, inv.M43, inv.M44 };
            Array.Copy(v, 0, ibm, i * 16, 16);
        }
        var skins = new List<object> { new Dictionary<string, object>
        {
            ["joints"] = Enumerable.Range(0, nb).ToArray(), ["inverseBindMatrices"] = bin.Floats(ibm, 16, "MAT4", target: null),
            ["skeleton"] = roots[0], ["name"] = Path.GetFileNameWithoutExtension(modelPath),
        } };

        // --- textures / materials
        var images = new List<object>(); var imageIndex = new Dictionary<string, int>();
        foreach (var t in h3d.Textures)
        {
            using var ms = new MemoryStream();
            t.ToBitmap().SaveAsPng(ms);
            images.Add(new Dictionary<string, object> { ["name"] = t.Name, ["mimeType"] = "image/png", ["bufferView"] = bin.Image(ms.ToArray()) });
            imageIndex[t.Name] = images.Count - 1;
        }
        // the material's sampler wrap matters: mirrored halves of faces/bodies use UVs outside 0..1 and read the
        // texture flipped with Mirror (Repeat would land on the wrong cell, e.g. a dark forehead)
        static int GlWrap(SPICA.PICA.Commands.PICATextureWrap w) => w switch
        {
            SPICA.PICA.Commands.PICATextureWrap.Mirror => 33648,
            SPICA.PICA.Commands.PICATextureWrap.ClampToEdge or SPICA.PICA.Commands.PICATextureWrap.ClampToBorder => 33071,
            _ => 10497,
        };
        var samplerList = new List<object>(); var samplerIndex = new Dictionary<(int, int), int>();
        var textures = new List<object>(); var texIndex = new Dictionary<(int, int), int>();
        var materials = new List<object>();
        foreach (var m in model.Materials)
        {
            var pbr = new Dictionary<string, object> { ["metallicFactor"] = 0.0, ["roughnessFactor"] = 1.0 };
            int cu = ColourUnit(m);
            if (TexName(m, cu) is string tn && imageIndex.TryGetValue(tn, out int img))
            {
                var mapper = m.TextureMappers[cu];
                var wrap = (GlWrap(mapper.WrapU), GlWrap(mapper.WrapV));
                if (!samplerIndex.TryGetValue(wrap, out int si))
                {
                    samplerList.Add(new Dictionary<string, object> { ["magFilter"] = 9729, ["minFilter"] = 9729, ["wrapS"] = wrap.Item1, ["wrapT"] = wrap.Item2 });
                    samplerIndex[wrap] = si = samplerList.Count - 1;
                }
                if (!texIndex.TryGetValue((img, si), out int ti))
                {
                    textures.Add(new Dictionary<string, object> { ["source"] = img, ["sampler"] = si });
                    texIndex[(img, si)] = ti = textures.Count - 1;
                }
                pbr["baseColorTexture"] = new Dictionary<string, object> { ["index"] = ti };
            }
            // alpha as the game draws it (same rule as tools/model_tool.py): alpha test -> MASK at its reference,
            // a real blend function -> BLEND, else OPAQUE. Many textures keep other data in alpha (m043's body is
            // 99 % "transparent"), so forcing MASK made whole models vanish in Blender's material preview.
            var mat = new Dictionary<string, object> { ["name"] = m.Name, ["pbrMetallicRoughness"] = pbr, ["doubleSided"] = true };
            var mp = m.MaterialParams;
            var bf = mp.BlendFunction;
            if (mp.AlphaTest.Enabled && (mp.AlphaTest.Function == SPICA.PICA.Commands.PICATestFunc.Greater || mp.AlphaTest.Function == SPICA.PICA.Commands.PICATestFunc.Gequal))
            { mat["alphaMode"] = "MASK"; mat["alphaCutoff"] = Math.Round(mp.AlphaTest.Reference / 255.0, 3); }
            else if (!(bf.ColorSrcFunc == SPICA.PICA.Commands.PICABlendFunc.One && bf.ColorDstFunc == SPICA.PICA.Commands.PICABlendFunc.Zero))
                mat["alphaMode"] = "BLEND";
            materials.Add(mat);
        }

        // --- meshes (one glTF mesh per H3D mesh, each on its own node with the skin)
        var meshes = new List<object>();
        var meshNodes = new List<int>();
        int mi = 0;
        // alternate meshes of one part (L_Hand01_MS .. L_Hand05_MS): the game switches them with visibility
        // animations; the lowest number is the default one
        string NodeName(SPICA.Formats.CtrH3D.Model.Mesh.H3DMesh m, int i) => m.NodeIndex >= 0 && m.NodeIndex < model.MeshNodesTree.Count ? model.MeshNodesTree.Find(m.NodeIndex) : $"mesh{i}";
        var variantRe = new System.Text.RegularExpressions.Regex(@"^(.*?)(\d{2})(_MS.*)$");
        var groups = model.Meshes.Select((m, i) => NodeName(m, i)).Select(n => variantRe.Match(n)).Where(m => m.Success)
            .GroupBy(m => m.Groups[1].Value + "##" + m.Groups[3].Value).Where(g => g.Select(x => x.Groups[2].Value).Distinct().Count() > 1)
            .ToDictionary(g => g.Key, g => g.Min(x => x.Groups[2].Value)!);
        int skipped = 0;
        foreach (var mesh in model.Meshes)
        {
            if (!outlines && NodeName(mesh, mi).EndsWith("_Outline")) { mi++; skipped++; continue; }
            var wv = SPICA.Formats.Common.MeshTransform.GetWorldSpaceVertices(skel, mesh);
            var raw = mesh.GetVertices();
            int n = wv.Length;
            var pos = new float[n * 3]; var nrm = new float[n * 3]; var uv = new float[n * 2];
            var joints = new ushort[n * 4]; var weights = new float[n * 4];
            var mm = model.Materials[mesh.MaterialIndex];
            int unit = ColourUnit(mm);
            var tm = mm.MaterialParams.TextureCoords[unit].GetTransform();
            int uvSet = UvSet(mm, unit);
            var uvAttr = uvSet switch { 1 => SPICA.PICA.Commands.PICAAttributeName.TexCoord1, 2 => SPICA.PICA.Commands.PICAAttributeName.TexCoord2, _ => SPICA.PICA.Commands.PICAAttributeName.TexCoord0 };
            if (!mesh.Attributes.Any(a => a.Name == uvAttr)) uvSet = 0;   // only one UV attribute stored
            bool hasNormal = false;
            for (int i = 0; i < n; i++)
            {
                pos[3 * i] = wv[i].Position.X; pos[3 * i + 1] = wv[i].Position.Y; pos[3 * i + 2] = wv[i].Position.Z;
                var nv = new Vector3(wv[i].Normal.X, wv[i].Normal.Y, wv[i].Normal.Z);
                if (nv.LengthSquared() > 1e-8f) { nv = Vector3.Normalize(nv); hasNormal = true; } else nv = Vector3.UnitY;
                nrm[3 * i] = nv.X; nrm[3 * i + 1] = nv.Y; nrm[3 * i + 2] = nv.Z;
                var tc = uvSet switch { 1 => wv[i].TexCoord1, 2 => wv[i].TexCoord2, _ => wv[i].TexCoord0 };
                float u = tc.X, w = tc.Y;
                uv[2 * i] = u * tm.M11 + w * tm.M21 + tm.M41;
                uv[2 * i + 1] = 1 - (u * tm.M12 + w * tm.M22 + tm.M42);
                weights[4 * i] = 1;   // overwritten below for every vertex a submesh uses
            }
            var done = new bool[n];
            var idx = new List<uint>();
            foreach (var sm in mesh.SubMeshes)
            {
                foreach (ushort v in sm.Indices)
                {
                    idx.Add(v);
                    if (done[v]) continue;
                    done[v] = true;
                    var rv = raw[v];
                    float sum = 0;
                    for (int k = 0; k < 4; k++) { joints[4 * v + k] = 0; weights[4 * v + k] = 0; }
                    if (sm.Skinning == SPICA.Formats.CtrH3D.Model.Mesh.H3DSubMeshSkinning.Smooth)
                    {
                        for (int k = 0; k < 4; k++)
                        {
                            float wk = rv.Weights[k]; int bk = rv.Indices[k];
                            if (wk > 0 && bk < sm.BoneIndices.Length) { joints[4 * v + k] = (ushort)sm.BoneIndices[bk]; weights[4 * v + k] = wk; sum += wk; }
                        }
                    }
                    else if (sm.BoneIndices.Length > 0)
                    {
                        joints[4 * v] = (ushort)sm.BoneIndices[Math.Min(rv.Indices[0], sm.BoneIndices.Length - 1)]; weights[4 * v] = 1; sum = 1;
                    }
                    if (sum <= 0) { weights[4 * v] = 1; sum = 1; }
                    for (int k = 0; k < 4; k++) weights[4 * v + k] /= sum;
                }
            }
            var attrs = new Dictionary<string, object>
            {
                ["POSITION"] = bin.Floats(pos, 3, "VEC3", minmax: true),
                ["TEXCOORD_0"] = bin.Floats(uv, 2, "VEC2"),
                ["JOINTS_0"] = bin.UShorts(joints, 4, "VEC4", 34962),
                ["WEIGHTS_0"] = bin.Floats(weights, 4, "VEC4"),
            };
            if (hasNormal) attrs["NORMAL"] = bin.Floats(nrm, 3, "VEC3");
            var name = NodeName(mesh, mi);
            meshes.Add(new Dictionary<string, object>
            {
                ["name"] = name,
                ["primitives"] = new[] { new Dictionary<string, object> { ["attributes"] = attrs, ["indices"] = bin.UInts(idx.ToArray()), ["material"] = mesh.MaterialIndex, ["mode"] = 4 } },
            });
            var node = new Dictionary<string, object> { ["name"] = $"{name}_{mi}", ["mesh"] = meshes.Count - 1, ["skin"] = 0 };
            var vm = variantRe.Match(name);
            // same marker as tools/model_tool.py: the viewer's Open in Blender imports these hidden
            if (vm.Success && groups.TryGetValue(vm.Groups[1].Value + "##" + vm.Groups[3].Value, out var first) && vm.Groups[2].Value != first)
                node["extras"] = new Dictionary<string, object> { ["dqxi_hidden"] = true };
            nodes.Add(node);
            meshNodes.Add(nodes.Count - 1);
            mi++;
        }

        // --- animations
        var animations = new List<object>();
        var byName = new Dictionary<string, int>();
        for (int i = 0; i < nb; i++) byName[bones[i].Name] = i;
        if (animList != null)
        {
            var cache = new Dictionary<string, H3D>();
            foreach (var line in File.ReadLines(animList))
            {
                var parts = line.Split('\t');
                if (parts.Length < 2) continue;
                if (!cache.TryGetValue(parts[0], out var ah)) cache[parts[0]] = ah = H3D.Open(File.ReadAllBytes(parts[0]));
                foreach (var anim in ah.SkeletalAnimations.Where(a => parts[1] == "*" || a.Name == parts[1]))
                {
                    var src = new List<(int bone, object content)>();
                    foreach (var e in anim.Elements)
                        if (byName.TryGetValue(e.Name, out int bi) && (e.Content is H3DAnimTransform || e.Content is H3DAnimQuatTransform || e.Content is H3DAnimMtxTransform))
                            src.Add((bi, e.Content));
                    if (src.Count == 0) continue;
                    var plan = Compat.MakePlan(bones, bindWorld, src.Select(t => t.bone).ToHashSet());
                    var restLocal = Enumerable.Range(0, nb).Select(i => plan.RestLocal(i)).ToArray();
                    var moved = new bool[nb];
                    foreach (var (bi, _) in src) moved[bi] = true;
                    for (int i = 0; i < nb; i++) if (plan.Targets[i].Count > 0) moved[i] = true;
                    int frames = Math.Max(1, (int)Math.Ceiling(anim.FramesCount) + 1);
                    var T = new float[nb][]; var R = new float[nb][]; var S = new float[nb][];
                    for (int i = 0; i < nb; i++) if (moved[i]) { T[i] = new float[frames * 3]; R[i] = new float[frames * 4]; S[i] = new float[frames * 3]; }
                    var local = new Matrix4x4[nb]; var world = new Matrix4x4[nb];
                    for (int f = 0; f < frames; f++)
                    {
                        Array.Copy(restLocal, local, nb);
                        foreach (var (bi, c) in src) { var m = plan.Local(bi, c, f); if (m.HasValue) local[bi] = m.Value; }
                        Compat.Evaluate(plan, bones, local, world);
                        for (int i = 0; i < nb; i++)
                        {
                            if (!moved[i]) continue;
                            int p = bones[i].ParentIndex;
                            var lm = world[i];
                            if (p >= 0) { Matrix4x4.Invert(world[p], out var ip); lm = world[i] * ip; }
                            var t = Trs(lm, out var r, out var s);
                            // keep quaternions on one hemisphere so Blender interpolates the short way
                            if (f > 0 && R[i][4 * f - 4] * r[0] + R[i][4 * f - 3] * r[1] + R[i][4 * f - 2] * r[2] + R[i][4 * f - 1] * r[3] < 0)
                                for (int k = 0; k < 4; k++) r[k] = -r[k];
                            Array.Copy(t, 0, T[i], 3 * f, 3); Array.Copy(r, 0, R[i], 4 * f, 4); Array.Copy(s, 0, S[i], 3 * f, 3);
                        }
                    }
                    var times = Enumerable.Range(0, frames).Select(f => f / 30f).ToArray();
                    int input = bin.Floats(times, 1, "SCALAR", minmax: true, target: null);
                    var samplers = new List<object>(); var channels = new List<object>();
                    for (int i = 0; i < nb; i++)
                    {
                        if (!moved[i]) continue;
                        foreach (var (path, data, comps, type) in new[] { ("translation", T[i], 3, "VEC3"), ("rotation", R[i], 4, "VEC4"), ("scale", S[i], 3, "VEC3") })
                        {
                            samplers.Add(new Dictionary<string, object> { ["input"] = input, ["output"] = bin.Floats(data, comps, type, target: null), ["interpolation"] = "LINEAR" });
                            channels.Add(new Dictionary<string, object> { ["sampler"] = samplers.Count - 1, ["target"] = new Dictionary<string, object> { ["node"] = i, ["path"] = path } });
                        }
                    }
                    animations.Add(new Dictionary<string, object> { ["name"] = parts.Length > 2 && parts[2].Length > 0 ? parts[2] + "/" + anim.Name : anim.Name, ["samplers"] = samplers, ["channels"] = channels });
                }
            }
        }

        var gltf = new Dictionary<string, object>
        {
            ["asset"] = new Dictionary<string, object> { ["version"] = "2.0", ["generator"] = "DQXI Disassemblr SpicaRef gltf" },
            ["scene"] = 0,
            ["scenes"] = new[] { new Dictionary<string, object> { ["nodes"] = roots.Concat(meshNodes).ToArray() } },
            ["nodes"] = nodes, ["skins"] = skins, ["meshes"] = meshes, ["materials"] = materials,
            ["buffers"] = new[] { new Dictionary<string, object> { ["byteLength"] = 0 } },
            ["bufferViews"] = bin.Views, ["accessors"] = bin.Accessors,
        };
        if (images.Count > 0)
        {
            gltf["images"] = images;
            if (textures.Count > 0) { gltf["textures"] = textures; gltf["samplers"] = samplerList; }
        }
        if (animations.Count > 0) gltf["animations"] = animations;
        while (bin.Data.Length % 4 != 0) bin.Data.WriteByte(0);
        ((Dictionary<string, object>[])gltf["buffers"])[0]["byteLength"] = (int)bin.Data.Length;
        var json = System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(gltf));
        int jsonLen = (json.Length + 3) & ~3;
        var binBytes = bin.Data.ToArray();
        using (var fs = File.Create(outPath))
        using (var w = new BinaryWriter(fs))
        {
            w.Write(0x46546C67u); w.Write(2u); w.Write((uint)(12 + 8 + jsonLen + 8 + binBytes.Length));
            w.Write((uint)jsonLen); w.Write(0x4E4F534Au); w.Write(json); for (int i = json.Length; i < jsonLen; i++) w.Write((byte)' ');
            w.Write((uint)binBytes.Length); w.Write(0x004E4942u); w.Write(binBytes);
        }
        Console.WriteLine($"{nb} joints, {meshes.Count} meshes ({skipped} outline shells skipped), {images.Count} textures, {animations.Count} animations -> {outPath}");
        return 0;
    }
}
