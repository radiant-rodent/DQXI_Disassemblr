// `compat <models.txt> <anims.txt> <out.json>`: which skeletal animations actually work on which rig.
//
// Models sharing one skeleton (same bone names, parents and rest translations) are tested once. For each distinct
// skeleton we keep ~1200 triangle edges of its mesh in bind pose with their skin weights. Every animation whose
// tracks are (>= 90%) bones of that skeleton is posed at 5 frames exactly as the viewer poses it (Pose.Local), the
// edges are skinned, and the score is the 98th percentile of the edge-length change max(posed/bind, bind/posed),
// worst frame. A working animation keeps the mesh near 1.0; a wrong one tears it apart. tools/anim_compat.py turns
// the scores into game_assets/animations/compat.json.
using System.Numerics;
using System.Text.Json;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Animation;
using SPICA.Formats.CtrH3D.Model;

static class Pose
{
    public static Matrix4x4 Euler(Vector3 sc, Vector3 ro, Vector3 tr)
    {
        var m = Matrix4x4.CreateScale(sc);
        m *= Matrix4x4.CreateRotationX(ro.X);
        m *= Matrix4x4.CreateRotationY(ro.Y);
        m *= Matrix4x4.CreateRotationZ(ro.Z);
        m *= Matrix4x4.CreateTranslation(tr);
        return m;
    }

    static float Axis(H3DFloatKeyFrameGroup g, float rest, float f) => g.KeyFrames.Count == 0 ? rest : g.GetFrameValue(f);

    // Local transform of `bone` at frame f under one animation element (null: unsupported content).
    public static Matrix4x4? Local(object content, H3DBone bone, int f) => Local(content, bone.Scale, bone.Rotation, bone.Translation, f);

    // rest S/R/T fill the axes a track does not key
    public static Matrix4x4? Local(object content, Vector3 rs, Vector3 rr, Vector3 rt, int f)
    {
        switch (content)
        {
            case H3DAnimTransform t:
                return Euler(new Vector3(Axis(t.ScaleX, rs.X, f), Axis(t.ScaleY, rs.Y, f), Axis(t.ScaleZ, rs.Z, f)),
                             new Vector3(Axis(t.RotationX, rr.X, f), Axis(t.RotationY, rr.Y, f), Axis(t.RotationZ, rr.Z, f)),
                             new Vector3(Axis(t.TranslationX, rt.X, f), Axis(t.TranslationY, rt.Y, f), Axis(t.TranslationZ, rt.Z, f)));
            case H3DAnimQuatTransform q:
            {
                var sc = q.HasScale ? q.GetScaleValue(f) : rs;
                var tr = q.HasTranslation ? q.GetTranslationValue(f) : rt;
                if (q.HasRotation)
                    return Matrix4x4.CreateScale(sc) * Matrix4x4.CreateFromQuaternion(q.GetRotationValue(f)) * Matrix4x4.CreateTranslation(tr);
                return Euler(sc, rr, tr);
            }
            case H3DAnimMtxTransform mt:
                return mt.GetTransform(f).ToMatrix4x4();
        }
        return null;
    }

    // inverse of Euler(): S, XYZ rotation (M = Rx*Ry*Rz, row vectors), T
    public static (Vector3 s, Vector3 r, Vector3 t) Decompose(Matrix4x4 m)
    {
        var r0 = new Vector3(m.M11, m.M12, m.M13); var r1 = new Vector3(m.M21, m.M22, m.M23); var r2 = new Vector3(m.M31, m.M32, m.M33);
        var sc = new Vector3(r0.Length(), r1.Length(), r2.Length());
        r0 /= sc.X; r1 /= sc.Y; r2 /= sc.Z;
        float y = MathF.Asin(Math.Clamp(-r0.Z, -1f, 1f)), x, z;
        if (MathF.Abs(r0.Z) < 0.9999f) { x = MathF.Atan2(r1.Z, r2.Z); z = MathF.Atan2(r0.Y, r0.X); }
        else { x = MathF.Atan2(-r2.Y, r1.Y); z = 0; }
        return (sc, new Vector3(x, y, z), m.Translation);
    }
}

static class Compat
{

    // ---- full-skeleton pose of one animation frame -------------------------------------------------------
    // DQXI motions are authored on a reduced skeleton: an animated bone's transform is relative to its nearest
    // *animated* ancestor, and bones without a track in between (shoulders, clavicles, thighs, extra spine
    // segments) are posed by the engine like aim constraints: they keep their rest offset from their parent and
    // rotate so their animated children land where the motion puts them (the bone lengths match exactly).
    public sealed class Plan
    {
        public int[] Par = Array.Empty<int>();          // effective parent (animated bones may skip untracked ones)
        public bool[] Animated = Array.Empty<bool>();
        public bool[] Final = Array.Empty<bool>();      // animated with an animated (or no) effective parent
        public List<int>[] Targets = Array.Empty<List<int>>();  // untracked bone -> first animated descendants
        public Vector3[][] RestOffset = Array.Empty<Vector3[]>(); // target positions in the bone's bind space
        public Vector3[] RS = Array.Empty<Vector3>(), RR = Array.Empty<Vector3>(), RT = Array.Empty<Vector3>(); // rest relative to Par
        public Matrix4x4 RestLocal(int i) => Pose.Euler(RS[i], RR[i], RT[i]);
        public Matrix4x4? Local(int i, object content, int f) => Pose.Local(content, RS[i], RR[i], RT[i], f);
    }

    public static Plan MakePlan(H3DBone[] bones, Matrix4x4[] bindWorld, ICollection<int> animated)
    {
        int nb = bones.Length;
        var pl = new Plan { Par = new int[nb], Animated = new bool[nb], Final = new bool[nb], Targets = new List<int>[nb], RestOffset = new Vector3[nb][],
                            RS = new Vector3[nb], RR = new Vector3[nb], RT = new Vector3[nb] };
        bool plain = Environment.GetEnvironmentVariable("DQXI_POSE") == "plain";
        for (int i = 0; i < nb; i++) { pl.Animated[i] = animated.Contains(i); pl.Targets[i] = new List<int>(); }
        for (int i = 0; i < nb; i++)
        {
            int p = bones[i].ParentIndex;
            pl.Par[i] = p;
            if (plain || !pl.Animated[i]) continue;
            int q = p;
            while (q >= 0 && !pl.Animated[q]) q = bones[q].ParentIndex;
            if (q < 0) continue;                     // no animated ancestor: plain hierarchy
            pl.Par[i] = q;
            for (int u = p; u != q; u = bones[u].ParentIndex) pl.Targets[u].Add(i);
        }
        for (int i = 0; i < nb; i++)
        {
            int p = pl.Par[i];
            pl.Final[i] = pl.Animated[i] && (p < 0 || pl.Animated[p]);
            Matrix4x4.Invert(bindWorld[i], out var inv);
            pl.RestOffset[i] = pl.Targets[i].Select(t => Vector3.Transform(bindWorld[t].Translation, inv)).ToArray();
            if (p == bones[i].ParentIndex) { pl.RS[i] = bones[i].Scale; pl.RR[i] = bones[i].Rotation; pl.RT[i] = bones[i].Translation; }
            else
            {
                Matrix4x4.Invert(bindWorld[p], out var ip);
                (pl.RS[i], pl.RR[i], pl.RT[i]) = Pose.Decompose(bindWorld[i] * ip);
            }
        }
        return pl;
    }

    static Quaternion Arc(Vector3 a, Vector3 b)
    {
        a = Vector3.Normalize(a); b = Vector3.Normalize(b);
        float d = Vector3.Dot(a, b);
        if (!float.IsFinite(d)) return Quaternion.Identity;
        if (d < -0.99999f)
        {
            var ax = Vector3.Cross(a, Vector3.UnitX);
            if (ax.LengthSquared() < 1e-6f) ax = Vector3.Cross(a, Vector3.UnitY);
            return Quaternion.CreateFromAxisAngle(Vector3.Normalize(ax), MathF.PI);
        }
        var c = Vector3.Cross(a, b);
        return Quaternion.Normalize(new Quaternion(c.X, c.Y, c.Z, 1 + d));
    }

    // world[] for one frame; local[] = rest transforms with the animated bones' sampled locals filled in
    public static void Evaluate(Plan pl, H3DBone[] bones, Matrix4x4[] local, Matrix4x4[] world)
    {
        int nb = bones.Length;
        for (int i = 0; i < nb; i++)
        {
            int p = pl.Par[i];
            world[i] = p >= 0 && p < i ? local[i] * world[p] : local[i];
        }
        for (int i = 0; i < nb; i++)
        {
            if (pl.Final[i]) continue;
            int p = pl.Par[i];
            var w0 = p >= 0 && p < i ? local[i] * world[p] : local[i];
            var tg = pl.Targets[i];
            if (tg.Count > 0)
            {
                var o = w0.Translation;
                // the two targets that constrain the rotation best: the farthest, then the least collinear
                int a = 0;
                for (int k = 1; k < tg.Count; k++)
                    if (Vector3.DistanceSquared(world[tg[k]].Translation, o) > Vector3.DistanceSquared(world[tg[a]].Translation, o)) a = k;
                var va = Vector3.TransformNormal(pl.RestOffset[i][a], w0);
                var ua = world[tg[a]].Translation - o;
                if (va.LengthSquared() > 1e-8f && ua.LengthSquared() > 1e-8f)
                {
                    var q = Arc(va, ua);
                    var axis = Vector3.Normalize(ua);
                    int b = -1; float best = 1e-4f;
                    for (int k = 0; k < tg.Count; k++)
                    {
                        if (k == a) continue;
                        var vk = Vector3.Transform(Vector3.TransformNormal(pl.RestOffset[i][k], w0), q);
                        var uk = world[tg[k]].Translation - o;
                        var pv = vk - Vector3.Dot(vk, axis) * axis; var pu = uk - Vector3.Dot(uk, axis) * axis;
                        float m = MathF.Min(pv.LengthSquared(), pu.LengthSquared());
                        if (m > best) { best = m; b = k; }
                    }
                    if (b >= 0)
                    {
                        var vk = Vector3.Transform(Vector3.TransformNormal(pl.RestOffset[i][b], w0), q);
                        var uk = world[tg[b]].Translation - o;
                        var pv = Vector3.Normalize(vk - Vector3.Dot(vk, axis) * axis); var pu = Vector3.Normalize(uk - Vector3.Dot(uk, axis) * axis);
                        float ang = MathF.Atan2(Vector3.Dot(Vector3.Cross(pv, pu), axis), Vector3.Dot(pv, pu));
                        q = Quaternion.Concatenate(q, Quaternion.CreateFromAxisAngle(axis, ang));
                    }
                    w0 = w0 * Matrix4x4.CreateTranslation(-o) * Matrix4x4.CreateFromQuaternion(q) * Matrix4x4.CreateTranslation(o);
                }
            }
            world[i] = w0;
        }
    }
    sealed class Skel
    {
        public string Key = "";
        public List<string> Models = new();
        public H3DBone[] Bones = Array.Empty<H3DBone>();
        public Dictionary<string, int> ByName = new();
        public Matrix4x4[] Rest = Array.Empty<Matrix4x4>();
        public Matrix4x4[] InvBind = Array.Empty<Matrix4x4>();
        public Matrix4x4[] BindWorld = Array.Empty<Matrix4x4>();
        public Vector3[] P = Array.Empty<Vector3>();      // edge endpoints, 2 per edge
        public int[] B = Array.Empty<int>();              // 4 bones per endpoint
        public float[] W = Array.Empty<float>();          // 4 weights per endpoint
        public float[] Len = Array.Empty<float>();        // bind length per edge
        public bool[] UnderBody = Array.Empty<bool>();   // has a skinned ancestor (not root motion)
        public bool[] Relevant = Array.Empty<bool>();    // skinned, or has a skinned descendant
        public float Size = 1;                            // bind-pose joint extent
    }

    const int MaxEdges = 1200;

    static string SkelKey(H3DDict<H3DBone> sk)
        => string.Join(";", sk.Select(b => $"{b.Name},{b.ParentIndex},{MathF.Round(b.Translation.X, 2)},{MathF.Round(b.Translation.Y, 2)},{MathF.Round(b.Translation.Z, 2)}"));

    static Skel? Build(H3D h3d)
    {
        var model = h3d.Models[0];
        var sk = model.Skeleton;
        int nb = sk.Count;
        var s = new Skel { Bones = sk.ToArray(), Rest = new Matrix4x4[nb], InvBind = new Matrix4x4[nb], BindWorld = new Matrix4x4[nb] };
        for (int i = 0; i < nb; i++)
        {
            s.ByName[sk[i].Name] = i;
            s.Rest[i] = sk[i].Transform;
            s.BindWorld[i] = sk[i].GetWorldTransform(sk);
            Matrix4x4.Invert(s.BindWorld[i], out s.InvBind[i]);
        }
        // all triangle edges of all meshes, with per-vertex bind position + weights
        var edges = new List<(Vector3 a, Vector3 b, int[] ba, float[] wa, int[] bb, float[] wb)>();
        foreach (var m in h3d.Models)
        {
            if (m.Skeleton.Count != nb) continue;
            foreach (var mesh in m.Meshes)
            {
                var wv = SPICA.Formats.Common.MeshTransform.GetWorldSpaceVertices(m.Skeleton, mesh);
                var raw = mesh.GetVertices();
                foreach (var sm in mesh.SubMeshes)
                {
                    (int[], float[]) Info(ushort idx)
                    {
                        var v = raw[idx];
                        var bi = new int[4]; var wt = new float[4];
                        if (sm.Skinning == SPICA.Formats.CtrH3D.Model.Mesh.H3DSubMeshSkinning.Smooth)
                        {
                            float sum = 0;
                            for (int k = 0; k < 4; k++)
                            {
                                float wk = v.Weights[k]; int bk = v.Indices[k];
                                if (wk > 0 && bk < sm.BoneIndices.Length) { bi[k] = sm.BoneIndices[bk]; wt[k] = wk; sum += wk; }
                            }
                            if (sum <= 0) wt[0] = 1; else for (int k = 0; k < 4; k++) wt[k] /= sum;
                        }
                        else if (sm.BoneIndices.Length > 0)
                        {
                            bi[0] = sm.BoneIndices[Math.Min(v.Indices[0], sm.BoneIndices.Length - 1)]; wt[0] = 1;
                        }
                        else wt[0] = 1;
                        return (bi, wt);
                    }
                    for (int i = 0; i + 2 < sm.Indices.Length; i += 3)
                        for (int e = 0; e < 3; e++)
                        {
                            ushort ia = sm.Indices[i + e], ib = sm.Indices[i + (e + 1) % 3];
                            var pa = wv[ia].Position; var pb = wv[ib].Position;
                            var a = new Vector3(pa.X, pa.Y, pa.Z); var b = new Vector3(pb.X, pb.Y, pb.Z);
                            if (Vector3.Distance(a, b) < 1e-4f) continue;
                            var (ba, wa) = Info(ia); var (bb2, wb) = Info(ib);
                            edges.Add((a, b, ba, wa, bb2, wb));
                        }
                }
            }
        }
        if (edges.Count == 0) return null;
        int step = Math.Max(1, edges.Count / MaxEdges);
        var pick = new List<int>();
        for (int i = 0; i < edges.Count; i += step) pick.Add(i);
        int n = pick.Count;
        s.P = new Vector3[2 * n]; s.B = new int[8 * n]; s.W = new float[8 * n]; s.Len = new float[n];
        for (int j = 0; j < n; j++)
        {
            var e = edges[pick[j]];
            s.P[2 * j] = e.a; s.P[2 * j + 1] = e.b;
            for (int k = 0; k < 4; k++)
            {
                s.B[8 * j + k] = e.ba[k]; s.W[8 * j + k] = e.wa[k];
                s.B[8 * j + 4 + k] = e.bb[k]; s.W[8 * j + 4 + k] = e.wb[k];
            }
            s.Len[j] = Vector3.Distance(e.a, e.b);
        }
        var skinned = new bool[nb];
        foreach (var e in edges) for (int k = 0; k < 4; k++) { if (e.wa[k] > 0) skinned[e.ba[k]] = true; if (e.wb[k] > 0) skinned[e.bb[k]] = true; }
        s.Relevant = new bool[nb];
        for (int i = nb - 1; i >= 0; i--) { if (skinned[i]) s.Relevant[i] = true; int p = sk[i].ParentIndex; if (s.Relevant[i] && p >= 0) s.Relevant[p] = true; }
        s.UnderBody = new bool[nb];
        for (int i = 0; i < nb; i++)
            for (int q = sk[i].ParentIndex; q >= 0; q = sk[q].ParentIndex) if (skinned[q]) { s.UnderBody[i] = true; break; }
        var jp = s.BindWorld.Select(m => m.Translation).ToArray();
        s.Size = Math.Max(1e-3f, Vector3.Distance(new Vector3(jp.Min(v => v.X), jp.Min(v => v.Y), jp.Min(v => v.Z)), new Vector3(jp.Max(v => v.X), jp.Max(v => v.Y), jp.Max(v => v.Z))));
        return s;
    }

    static Vector3 Skin(Skel s, Matrix4x4[] skin, int v)
    {
        var p = s.P[v];
        var r = Vector3.Zero;
        for (int k = 0; k < 4; k++)
        {
            float w = s.W[4 * v + k];
            if (w <= 0) continue;
            r += w * Vector3.Transform(p, skin[s.B[4 * v + k]]);
        }
        return r;
    }

    // worst-frame p98 edge stretch of one animation on one skeleton

    static bool JointLog = Environment.GetEnvironmentVariable("DQXI_JOINTLOG") == "1";
    static (float mesh, float joint) Score(Skel s, H3DAnimation anim, List<(int bone, object content)> tracks)
        => Score(s, anim, tracks, null);

    // dirs (optional): unit world direction of every body segment "parent>bone" at the 5 sampled frames
    static (float mesh, float joint) Score(Skel s, H3DAnimation anim, List<(int bone, object content)> tracks, Dictionary<string, Vector3[]>? dirs)
    {
        int nb = s.Bones.Length;
        var local = new Matrix4x4[nb]; var world = new Matrix4x4[nb]; var skin = new Matrix4x4[nb];
        var ratios = new float[s.Len.Length];
        float worst = 1, joint = 0;
        float last = Math.Max(0, anim.FramesCount);
        var plan = MakePlan(s.Bones, s.BindWorld, tracks.Select(t => t.bone).ToHashSet());
        var frames = new[] { 0, last * 0.25f, last * 0.5f, last * 0.75f, last };
        for (int fk = 0; fk < frames.Length; fk++)
        {
            float f = frames[fk];
            Array.Copy(s.Rest, local, nb);
            foreach (var (bi, c) in tracks)
            {
                var m = plan.Local(bi, c, (int)f);
                if (m.HasValue) local[bi] = m.Value;
            }
            Evaluate(plan, s.Bones, local, world);
            for (int i = 0; i < nb; i++) skin[i] = s.InvBind[i] * world[i];
            for (int j = 0; j < ratios.Length; j++)
            {
                float d = Vector3.Distance(Skin(s, skin, 2 * j), Skin(s, skin, 2 * j + 1));
                float r = d / s.Len[j];
                ratios[j] = float.IsFinite(r) ? (r < 1e-6f ? 1e6f : Math.Max(r, 1 / r)) : 1e6f;
            }
            Array.Sort(ratios);
            worst = Math.Max(worst, ratios[(int)(0.98 * (ratios.Length - 1))]);
            // joint fit: every bone segment (plain parent -> bone) that carries skin keeps its bind length
            for (int i = 0; i < nb; i++)
            {
                int p = s.Bones[i].ParentIndex;
                if (p < 0 || !s.Relevant[i] || !s.UnderBody[i]) continue;
                float db = Vector3.Distance(s.BindWorld[i].Translation, s.BindWorld[p].Translation);
                float da = Vector3.Distance(world[i].Translation, world[p].Translation);
                float je = MathF.Abs(da - db) / Math.Max(db, 0.05f * s.Size);
                if (JointLog && je > 0.05f) Console.WriteLine($"   joint f={f:F0} {s.Bones[i].Name} bind {db:F3} anim {da:F3} err {je:F2}");
                joint = Math.Max(joint, je);
                if (dirs != null && db > 0.03f * s.Size && da > 1e-5f)
                {
                    var key = s.Bones[p].Name + ">" + s.Bones[i].Name;
                    if (!dirs.TryGetValue(key, out var arr)) dirs[key] = arr = new Vector3[frames.Length];
                    arr[fk] = Vector3.Normalize(world[i].Translation - world[p].Translation);
                }
            }
            // orientation of every animated bone (its world X and Y axes): catches rigs whose bones use other rest
            // axes, which a one-bone clip (a head turn) would twist the wrong way
            if (dirs != null)
                foreach (var (bi, _) in tracks)
                {
                    if (!s.UnderBody[bi] || !s.Relevant[bi]) continue;
                    var wm = world[bi];
                    var ax = new Vector3(wm.M11, wm.M12, wm.M13); var ay = new Vector3(wm.M21, wm.M22, wm.M23);
                    if (ax.LengthSquared() < 1e-10f || ay.LengthSquared() < 1e-10f) continue;
                    foreach (var (key, v) in new[] { ("@" + s.Bones[bi].Name + ":x", ax), ("@" + s.Bones[bi].Name + ":y", ay) })
                    {
                        if (!dirs.TryGetValue(key, out var arr)) dirs[key] = arr = new Vector3[frames.Length];
                        arr[fk] = Vector3.Normalize(v);
                    }
                }
        }
        return (worst, joint);
    }


    // `compatdiag <model.bch> <anim.bch> <anim index>`: per-bone stretch and track values, to debug Score.
    public static int Diag(string modelPath, string animPath, int ai)
    {
        var h3d = H3D.Open(File.ReadAllBytes(modelPath));
        var s = Build(h3d)!;
        var a = H3D.Open(File.ReadAllBytes(animPath)).SkeletalAnimations[ai];
        var tracks = new List<(int, object)>();
        foreach (var e in a.Elements) if (s.ByName.TryGetValue(e.Name, out int bi)) tracks.Add((bi, e.Content));
        Console.WriteLine($"{a.Name}: {a.FramesCount} frames, {a.Elements.Count} elements, {tracks.Count} on rig, score {Score(s, a, tracks)}");
        int nb = s.Bones.Length;
        var local = (Matrix4x4[])s.Rest.Clone(); var world = new Matrix4x4[nb]; var skin = new Matrix4x4[nb];
        var dplan = MakePlan(s.Bones, s.BindWorld, tracks.Select(t => t.Item1).ToHashSet());
        foreach (var (bi, c) in tracks) { var m = dplan.Local(bi, c, 0); if (m.HasValue) local[bi] = m.Value; }
        // self-check: rest relative to the effective parent round-trips through Decompose/Euler
        float err = 0;
        for (int i = 0; i < nb; i++) { int p = dplan.Par[i]; if (p < 0) continue; Matrix4x4.Invert(s.BindWorld[p], out var ip); var d = dplan.RestLocal(i) - s.BindWorld[i] * ip; err = Math.Max(err, new[] { d.M11, d.M12, d.M13, d.M21, d.M22, d.M23, d.M31, d.M32, d.M33, d.M41, d.M42, d.M43 }.Max(MathF.Abs)); }
        Console.WriteLine($"rest round-trip max error {err:E2}");
        Evaluate(dplan, s.Bones, local, world);
        for (int i = 0; i < nb; i++) skin[i] = s.InvBind[i] * world[i];
        var per = new double[nb]; var cnt = new int[nb];
        for (int j = 0; j < s.Len.Length; j++)
        {
            float d = Vector3.Distance(Skin(s, skin, 2 * j), Skin(s, skin, 2 * j + 1)); float r = d / s.Len[j]; r = Math.Max(r, 1 / r);
            int b = s.B[8 * j]; per[b] += r; cnt[b]++;
        }
        var kinds = new Dictionary<int, string>();
        foreach (var (bi, c) in tracks) kinds[bi] = c.GetType().Name.Replace("H3DAnim", "");
        for (int i = 0; i < nb; i++)
        {
            var b = s.Bones[i];
            Matrix4x4.Decompose(local[i], out var asc, out var aq, out var at);
            Console.WriteLine($"{i,3} {b.Name,-16} p={b.ParentIndex,3} flags={b.Flags} {(kinds.TryGetValue(i, out var k) ? k : "-"),-14} stretch={(cnt[i] > 0 ? per[i] / cnt[i] : 0):F2} n={cnt[i],4}  restS={b.Scale} restR={b.Rotation} restT={b.Translation}  animS={asc} animT={at}");
        }
        return 0;
    }


    // `chan <anim.bch> <anim index> <bone>`: raw flags and per-channel keys of one bone track.
    public static int Chan(string animPath, int ai, string boneName)
    {
        var a = H3D.Open(File.ReadAllBytes(animPath)).SkeletalAnimations[ai];
        var e = a.Elements.First(x => x.Name == boneName);
        Console.WriteLine($"{a.Name} {e.Name} {e.Content.GetType().Name} prim={e.PrimitiveType} target={e.TargetType}");
        if (e.Content is H3DAnimTransform t)
        {
            var fl = typeof(H3DAnimTransform).GetField("Flags", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!.GetValue(t);
            Console.WriteLine($"flags=0x{Convert.ToUInt32(fl):X8} {fl}");
            var ch = new (string, H3DFloatKeyFrameGroup)[] { ("SX", t.ScaleX), ("SY", t.ScaleY), ("SZ", t.ScaleZ), ("RX", t.RotationX), ("RY", t.RotationY), ("RZ", t.RotationZ), ("TX", t.TranslationX), ("TY", t.TranslationY), ("TZ", t.TranslationZ) };
            foreach (var (n, g) in ch)
                Console.WriteLine($"  {n} keys={g.KeyFrames.Count} interp={g.InterpolationType} q={g.Quantization} " + string.Join(" ", g.KeyFrames.Take(6).Select(k => $"{k.Frame}:{k.Value:F3}")));
        }
        return 0;
    }


    // `posedobj <model.bch> <anim.bch> <anim index> <frame> <out.obj>`: the model's meshes posed at one frame (the
    // same evaluation as the viewer), for eyeballing a pose. Frame -1 writes the bind pose.
    public static int PosedObj(string modelPath, string animPath, int ai, int frame, string outPath)
    {
        var h3d = H3D.Open(File.ReadAllBytes(modelPath));
        var model = h3d.Models[0];
        var bones = model.Skeleton.ToArray(); int nb = bones.Length;
        var bindWorld = bones.Select(b => b.GetWorldTransform(model.Skeleton)).ToArray();
        var byName = new Dictionary<string, int>(); for (int i = 0; i < nb; i++) byName[bones[i].Name] = i;
        var world = (Matrix4x4[])bindWorld.Clone();
        if (frame >= 0)
        {
            var a = H3D.Open(File.ReadAllBytes(animPath)).SkeletalAnimations[ai];
            var tracks = new List<(int, object)>();
            foreach (var e in a.Elements) if (byName.TryGetValue(e.Name, out int bi)) tracks.Add((bi, e.Content));
            var plan = MakePlan(bones, bindWorld, tracks.Select(t => t.Item1).ToHashSet());
            var local = Enumerable.Range(0, nb).Select(i => plan.RestLocal(i)).ToArray();
            foreach (var (bi, c) in tracks) { var m = plan.Local(bi, c, frame); if (m.HasValue) local[bi] = m.Value; }
            Evaluate(plan, bones, local, world);
        }
        var skin = new Matrix4x4[nb];
        for (int i = 0; i < nb; i++) { Matrix4x4.Invert(bindWorld[i], out var inv); skin[i] = inv * world[i]; }
        var sb = new System.Text.StringBuilder(); int baseIndex = 1;
        foreach (var mesh in model.Meshes)
        {
            var wv = SPICA.Formats.Common.MeshTransform.GetWorldSpaceVertices(model.Skeleton, mesh);
            var raw = mesh.GetVertices();
            var pos = new Vector3[wv.Length]; var done = new bool[wv.Length];
            foreach (var sm in mesh.SubMeshes)
                foreach (ushort idx in sm.Indices)
                {
                    if (done[idx]) continue; done[idx] = true;
                    var v = raw[idx]; var p = new Vector3(wv[idx].Position.X, wv[idx].Position.Y, wv[idx].Position.Z);
                    var r = Vector3.Zero; float sum = 0;
                    if (sm.Skinning == SPICA.Formats.CtrH3D.Model.Mesh.H3DSubMeshSkinning.Smooth)
                        for (int k = 0; k < 4; k++) { float w = v.Weights[k]; int bk = v.Indices[k]; if (w > 0 && bk < sm.BoneIndices.Length) { r += w * Vector3.Transform(p, skin[sm.BoneIndices[bk]]); sum += w; } }
                    else if (sm.BoneIndices.Length > 0) { r = Vector3.Transform(p, skin[sm.BoneIndices[Math.Min(v.Indices[0], sm.BoneIndices.Length - 1)]]); sum = 1; }
                    pos[idx] = sum > 0 ? r / sum : p;
                }
            foreach (var p in pos) sb.AppendLine($"v {p.X} {p.Y} {p.Z}");
            foreach (var sm in mesh.SubMeshes)
                for (int i = 0; i + 2 < sm.Indices.Length; i += 3)
                    sb.AppendLine($"f {sm.Indices[i] + baseIndex} {sm.Indices[i + 1] + baseIndex} {sm.Indices[i + 2] + baseIndex}");
            baseIndex += pos.Length;
        }
        File.WriteAllText(outPath, sb.ToString());
        return 0;
    }

    public static int Run(string modelsList, string animsList, string outPath)
    {
        var skels = new Dictionary<string, Skel>();
        var lockObj = new object();
        int nm = 0;
        Parallel.ForEach(File.ReadLines(modelsList).Select(l => l.Trim()).Where(l => l.Length > 0).ToList(), path =>
        {
            try
            {
                var h3d = H3D.Open(File.ReadAllBytes(path));
                if (h3d.Models.Count == 0 || h3d.Models[0].Skeleton.Count < 2) return;
                var key = SkelKey(h3d.Models[0].Skeleton);
                lock (lockObj)
                {
                    nm++;
                    if (skels.TryGetValue(key, out var have)) { have.Models.Add(path); return; }
                    skels[key] = new Skel { Key = key };   // placeholder, built below
                    skels[key].Models.Add(path);
                }
                var built = Build(h3d);
                lock (lockObj)
                {
                    var models = skels[key].Models;
                    if (built == null) { skels.Remove(key); return; }
                    built.Key = key; built.Models = models;
                    skels[key] = built;
                }
            }
            catch (Exception e) { Console.Error.WriteLine($"{path}: {e.Message}"); }
        });
        var list = skels.Values.ToList();
        Console.WriteLine($"{nm} rigged models -> {list.Count} distinct skeletons");

        var animFiles = File.ReadLines(animsList).Select(l => l.Trim()).Where(l => l.Length > 0).ToList();
        // results[skel] = list of (file index, anim index, score, coverage)
        var results = list.Select(_ => new List<object[]>()).ToArray();
        var names = new string[animFiles.Count][];
        int done = 0;
        long pairs = 0;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        Parallel.For(0, animFiles.Count, fi =>
        {
            H3D h3d;
            try { h3d = H3D.Open(File.ReadAllBytes(animFiles[fi])); }
            catch (Exception e) { Console.Error.WriteLine($"{animFiles[fi]}: {e.Message}"); names[fi] = Array.Empty<string>(); return; }
            var anims = h3d.SkeletalAnimations.ToList();
            names[fi] = anims.Select(a => a.Name).ToArray();
            for (int ai = 0; ai < anims.Count; ai++)
            {
                var a = anims[ai];
                var els = a.Elements.Where(e => e.Content is H3DAnimTransform || e.Content is H3DAnimQuatTransform || e.Content is H3DAnimMtxTransform).ToList();
                if (els.Count == 0) continue;
                var cand = new List<(int si, float mesh, float joint, float cov, Dictionary<string, Vector3[]> dirs)>();
                for (int si = 0; si < list.Count; si++)
                {
                    var s = list[si];
                    var tracks = new List<(int, object)>();
                    foreach (var e in els)
                        if (s.ByName.TryGetValue(e.Name, out int bi)) tracks.Add((bi, e.Content));
                    if (tracks.Count == 0 || tracks.Count < 0.9 * els.Count) continue;
                    float sc, jt; var dirs = new Dictionary<string, Vector3[]>();
                    try { (sc, jt) = Score(s, a, tracks, dirs); } catch { sc = 1e6f; jt = 1e6f; }
                    Interlocked.Increment(ref pairs);
                    cand.Add((si, sc, jt, (float)tracks.Count / els.Count, dirs));
                }
                if (cand.Count == 0) continue;
                // reference: the rig this motion fits best (its own family, normally): smallest joint error, then the one
                // where it drives the most skinned bones (a head-turn clip's own rig, not a rig it barely touches)
                var rf = cand.OrderBy(c => MathF.Round(c.joint, 2)).ThenByDescending(c => c.dirs.Count).ThenByDescending(c => c.cov).ThenBy(c => c.mesh).First();
                foreach (var c in cand)
                {
                    // p90 over shared body segments of the mean angle (deg) to the reference pose; -1 = too few shared
                    var angs = new List<float>();
                    foreach (var (k, v) in c.dirs)
                    {
                        if (!rf.dirs.TryGetValue(k, out var w)) continue;
                        float sum = 0; int n = 0;
                        for (int j = 0; j < v.Length; j++)
                            if (v[j] != Vector3.Zero && w[j] != Vector3.Zero) { sum += MathF.Acos(Math.Clamp(Vector3.Dot(v[j], w[j]), -1f, 1f)); n++; }
                        if (n > 0) angs.Add(sum / n * 180 / MathF.PI);
                    }
                    angs.Sort();
                    float dir = angs.Count >= 2 ? angs[(int)(0.9 * (angs.Count - 1))] : -1;
                    lock (results[c.si]) results[c.si].Add(new object[] { fi, ai, MathF.Round(Math.Min(c.mesh, 1e6f), 3), MathF.Round(Math.Min(c.joint, 1e6f), 3),
                        MathF.Round(c.cov, 2), MathF.Round(dir, 1), MathF.Round(Math.Min(rf.joint, 1e6f), 3), c.si == rf.si ? 1 : 0 });
                }
            }
            int d = Interlocked.Increment(ref done);
            if (d % 200 == 0) Console.WriteLine($"  {d}/{animFiles.Count} animation files, {pairs} pairs, {sw.Elapsed.TotalSeconds:F0}s");
        });
        var outObj = new Dictionary<string, object>
        {
            ["anim_files"] = animFiles,
            ["anim_names"] = names,
            ["skeletons"] = list.Select((s, i) => new Dictionary<string, object>
            {
                ["models"] = s.Models.OrderBy(m => m).ToList(),
                ["bones"] = s.Bones.Length,
                ["edges"] = s.Len.Length,
                ["results"] = results[i],
            }).ToList(),
        };
        File.WriteAllText(outPath, JsonSerializer.Serialize(outObj));
        Console.WriteLine($"{pairs} pairs scored in {sw.Elapsed.TotalSeconds:F0}s -> {outPath}");
        return 0;
    }
}
