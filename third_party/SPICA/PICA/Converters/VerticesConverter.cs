using SPICA.Formats.CtrH3D.Model.Mesh;
using SPICA.PICA.Commands;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;

namespace SPICA.PICA.Converters
{
    public static class VerticesConverter
    {
        public static PICAVertex[] GetVertices(H3DMesh Mesh)
        {
            if (Mesh.RawBuffer.Length == 0) return new PICAVertex[0];

            float[] Elems = new float[4];

            PICAVertex[] Output = new PICAVertex[Mesh.RawBuffer.Length / Mesh.VertexStride];

            using (MemoryStream MS = new MemoryStream(Mesh.RawBuffer))
            {
                BinaryReader Reader = new BinaryReader(MS);

                for (int Index = 0; Index < Output.Length; Index++)
                {
                    PICAVertex Out = new PICAVertex();

                    MS.Seek(Index * Mesh.VertexStride, SeekOrigin.Begin);

                    int bi = 0;
                    int wi = 0;

                    foreach (PICAAttribute Attrib in Mesh.Attributes)
                    {
                        AlignStream(MS, Attrib.Format);

                        for (int Elem = 0; Elem < Attrib.Elements; Elem++)
                        {
                            switch (Attrib.Format)
                            {
                                case PICAAttributeFormat.Byte:  Elems[Elem] = Reader.ReadSByte();  break;
                                case PICAAttributeFormat.Ubyte: Elems[Elem] = Reader.ReadByte();   break;
                                case PICAAttributeFormat.Short: Elems[Elem] = Reader.ReadInt16();  break;
                                case PICAAttributeFormat.Float: Elems[Elem] = Reader.ReadSingle(); break;
                            }                        }

                        Vector4 v = new Vector4(Elems[0], Elems[1], Elems[2], Elems[3]);

                        v *= Attrib.Scale;

                        if (Attrib.Name == PICAAttributeName.Position)
                        {
                            v += Mesh.PositionOffset;
                        }

                        switch (Attrib.Name)
                        {
                            case PICAAttributeName.Position:  Out.Position  = v; break;
                            case PICAAttributeName.Normal:    Out.Normal    = v; break;
                            case PICAAttributeName.Tangent:   Out.Tangent   = v; break;
                            case PICAAttributeName.Color:     Out.Color     = v; break;
                            case PICAAttributeName.TexCoord0: Out.TexCoord0 = v; break;
                            case PICAAttributeName.TexCoord1: Out.TexCoord1 = v; break;
                            case PICAAttributeName.TexCoord2: Out.TexCoord2 = v; break;

                            case PICAAttributeName.BoneIndex:
                                Out.Indices[bi++] = (int)v.X; if (Attrib.Elements == 1) break;
                                Out.Indices[bi++] = (int)v.Y; if (Attrib.Elements == 2) break;
                                Out.Indices[bi++] = (int)v.Z; if (Attrib.Elements == 3) break;
                                Out.Indices[bi++] = (int)v.W;                           break;

                            case PICAAttributeName.BoneWeight:
                                Out.Weights[wi++] =      v.X; if (Attrib.Elements == 1) break;
                                Out.Weights[wi++] =      v.Y; if (Attrib.Elements == 2) break;
                                Out.Weights[wi++] =      v.Z; if (Attrib.Elements == 3) break;
                                Out.Weights[wi++] =      v.W;                           break;
                        }
                    }

                    if (Mesh.FixedAttributes != null)
                    {
                        foreach (PICAFixedAttribute Attr in Mesh.FixedAttributes)
                        {
                            switch (Attr.Name)
                            {
                                case PICAAttributeName.Normal:
                                    Out.Normal = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                                case PICAAttributeName.Tangent:
                                    Out.Tangent = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                                case PICAAttributeName.Color:
                                    Out.Color = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                                case PICAAttributeName.TexCoord0:
                                    Out.TexCoord0 = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                                case PICAAttributeName.TexCoord1:
                                    Out.TexCoord1 = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                                case PICAAttributeName.TexCoord2:
                                    Out.TexCoord2 = new Vector4(Attr.Value.X, Attr.Value.Y, Attr.Value.Z, Attr.Value.W);
                                    break;
                            }
                        }

                        bool HasFixedIndices = Mesh.FixedAttributes.Any(x => x.Name == PICAAttributeName.BoneIndex);
                        bool HasFixedWeights = Mesh.FixedAttributes.Any(x => x.Name == PICAAttributeName.BoneWeight);

                        if (HasFixedIndices || HasFixedWeights)
                        {
                            foreach (PICAFixedAttribute Attr in Mesh.FixedAttributes)
                            {
                                switch (Attr.Name)
                                {
                                    case PICAAttributeName.BoneIndex:
                                        Out.Indices[0] = (int)Attr.Value.X;
                                        Out.Indices[1] = (int)Attr.Value.Y;
                                        Out.Indices[2] = (int)Attr.Value.Z;
                                        break;

                                    case PICAAttributeName.BoneWeight:
                                        Out.Weights[0] =      Attr.Value.X;
                                        Out.Weights[1] =      Attr.Value.Y;
                                        Out.Weights[2] =      Attr.Value.Z;
                                        break;
                                }
                            }
                        }
                    }

                    Output[Index] = Out;
                }
            }

            return Output;
        }

        public static int CalculateStride(IEnumerable<PICAAttribute> attributes, bool alignBy4 = false)
        {
            int VertexStride = 0;
            foreach (var att in attributes)
            {
                /*
             * Byte attributes that are not aligned on a 2 bytes boundary (for example, Byte Vector3)
             * needs to be aligned to a 2 byte boundary, so we insert a 1 byte dummy element to force alignment.
             * Attributes of the same type doesn't need to be aligned however.
             * For example:
             * A Byte Vector3 Normal followed by a Byte Vector4 Color, followed by a Short Vector2 TexCoord is
             * stored like this: NX NY NZ CR CG CB CA <Padding0> TX TX TY TY
             */
                if (att.Format != PICAAttributeFormat.Ubyte &&
                    att.Format != PICAAttributeFormat.Byte)
                {
                    VertexStride += VertexStride & 1;
                }

                int Size = att.Elements;

                switch (att.Format)
                {
                    case PICAAttributeFormat.Short: Size <<= 1; break;
                    case PICAAttributeFormat.Float: Size <<= 2; break;
                }

                VertexStride += Size;
            }
            VertexStride += VertexStride & 1;

            if (alignBy4)
            {
                //Make sure the stride is divisible into 4
                while (VertexStride % 4 != 0)
                    VertexStride += 1;
            }
            return VertexStride;
        }

        static int GetStride(PICAAttributeFormat format)
        {
            switch (format)
            {
                case PICAAttributeFormat.Byte:
                case PICAAttributeFormat.Ubyte:
                    return 1;
                case PICAAttributeFormat.Short:
                    return 2;
                case PICAAttributeFormat.Float:
                    return 4;
            }
            return 4;
        }

        public static byte[] GetBuffer(IEnumerable<PICAVertex> Vertices, IEnumerable<PICAAttribute> Attributes, int stride = 0)
        {
            if (stride == 0)
                stride = CalculateStride(Attributes);

            using (MemoryStream MS = new MemoryStream())
            {
                BinaryWriter Writer = new BinaryWriter(MS);

                foreach (PICAVertex Vertex in Vertices)
                {
                    var pos = Writer.BaseStream.Position;

                    int bi = 0;
                    int wi = 0;

                    foreach (PICAAttribute Attrib in Attributes)
                    {
                        AlignStream(MS, Attrib.Format);
                        for (int i = 0; i < Attrib.Elements; i++)
                        {
                            switch (Attrib.Name)
                            {
                                case PICAAttributeName.Position:   Write(Writer, Attrib, Vertex.Position,  i);  break;
                                case PICAAttributeName.Normal:     Write(Writer, Attrib, Vertex.Normal,    i);  break;
                                case PICAAttributeName.Tangent:    Write(Writer, Attrib, Vertex.Tangent,   i);  break;
                                case PICAAttributeName.Color:      Write(Writer, Attrib, Vertex.Color,     i);  break;
                                case PICAAttributeName.TexCoord0:  Write(Writer, Attrib, Vertex.TexCoord0, i);  break;
                                case PICAAttributeName.TexCoord1:  Write(Writer, Attrib, Vertex.TexCoord1, i);  break;
                                case PICAAttributeName.TexCoord2:  Write(Writer, Attrib, Vertex.TexCoord2, i);  break;
                                case PICAAttributeName.BoneIndex:  Write(Writer, Attrib, Vertex.Indices[bi++]); break;
                                case PICAAttributeName.BoneWeight: Write(Writer, Attrib, Vertex.Weights[wi++]); break;

								default: Write(Writer, Attrib, 0); break;
                            }
                        }
                    }
                    if (stride != 0)
                    {
                        while (Writer.BaseStream.Position < pos + stride) {
                            Writer.Write((byte)0);
                        }
                    }
                }

                return MS.ToArray();
            }
        }

        private static void Write(BinaryWriter Writer, PICAAttribute Attrib, Vector4 v, int i)
        {
            switch (i)
            {
                case 0: Write(Writer, Attrib, v.X); break;
                case 1: Write(Writer, Attrib, v.Y); break;
                case 2: Write(Writer, Attrib, v.Z); break;
                case 3: Write(Writer, Attrib, v.W); break;
            }
        }

        private static void Write(BinaryWriter Writer, PICAAttribute Attrib, float Value)
        {
            Value /= Attrib.Scale;

            if (Attrib.Format != PICAAttributeFormat.Float && Attrib.Name != PICAAttributeName.BoneIndex)
            {
                //Due to float lack of precision it's better to round the number,
                //because directly casting it will always use the lowest number that
                //may cause issues for values that float can't represent (like 0.1).
                Value = (float)Math.Round(Value);
            }

            switch (Attrib.Format)
            {
                case PICAAttributeFormat.Byte:  Writer.Write((sbyte)Value); break;
                case PICAAttributeFormat.Ubyte: Writer.Write((byte)Value);  break;
                case PICAAttributeFormat.Short: Writer.Write((short)Value); break;
                case PICAAttributeFormat.Float: Writer.Write(Value);        break;
            }
        }

        private static void AlignStream(Stream Strm, PICAAttributeFormat Fmt)
        {
            //Short and Float types needs to be aligned into 2 bytes boundaries.
            //TODO: Float may actually need a 4 bytes alignment, need to test later.
            if (Fmt != PICAAttributeFormat.Byte &&
                Fmt != PICAAttributeFormat.Ubyte)
            {
                Strm.Position += Strm.Position & 1;
            }
        }
    }
}
