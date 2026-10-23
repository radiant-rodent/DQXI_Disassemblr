using SPICA.Serialization;
using SPICA.Serialization.Attributes;
using SPICA.Serialization.Serializer;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;

namespace SPICA.Formats.CtrH3D.Model.Mesh
{
    public struct H3DSubMeshCulling 
    {
        //TODO
        public List<CullingNodeData> CullingNodes;
        public List<BoundingData> Boundings;
        public List<SubMeshCullingFace> SubMeshes;
        public ushort BoolUniforms;
        public short BoneIndex;

        [Ignore] public ushort MaxIndex
        {
            get
            {
                ushort face = 0;
                foreach (var SM in SubMeshes)
                {
                    face = Math.Max(SM.Indices.Max(x => x), face);
                }
                return face;
            }
        }
    }

    [Inline]
    public class CullingNodeData
    {
        public byte Left;
        public byte Right;
        public byte Next;
        public byte SubMeshIndex;
        public uint SubMeshCount;
    }

    [Inline]
    public class BoundingData
    {
        public Vector3 Center;
        public Vector3 Extent;
    }

    [Inline]
    public class SubMeshCullingFace : ICustomSerialization
    {
        private uint BufferAddress;
        private uint BufferCount;

        [Ignore]
        public ushort[] Indices;
        public int MaxIndex
        {
            get
            {
                int Max = 0;

                foreach (ushort Index in Indices)
                {
                    if (Max < Index)
                        Max = Index;
                }

                return Max;
            }
        }

        void ICustomSerialization.Deserialize(BinaryDeserializer Deserializer)
        {
            long Position = Deserializer.BaseStream.Position;
            bool Is16BitsIdx = (BufferAddress >> 31) != 0;

            Indices = new ushort[BufferCount];

            Deserializer.BaseStream.Seek(BufferAddress & 0x7fffffff, SeekOrigin.Begin);

            for (int Index = 0; Index < BufferCount; Index++)
            {
                if (Is16BitsIdx)
                    Indices[Index] = Deserializer.Reader.ReadUInt16();
                else
                    Indices[Index] = Deserializer.Reader.ReadByte();
            }

            Deserializer.BaseStream.Seek(Position, SeekOrigin.Begin);
        }

        bool ICustomSerialization.Serialize(BinarySerializer Serializer)
        {
            BufferCount = (uint)Indices.Length;

            H3DSection Section = H3DSection.RawDataIndex16;
            object Data;

            if (MaxIndex <= byte.MaxValue)
            {
                Section = H3DSection.RawDataIndex8;

                byte[] Buffer = new byte[Indices.Length];

                for (int Index = 0; Index < Indices.Length; Index++)
                {
                    Buffer[Index] = (byte)Indices[Index];
                }

                Data = Buffer;
            }
            else
            {
                Data = Indices;
            }

            long Position = Serializer.BaseStream.Position;

            H3DRelocator.AddCmdReloc(Serializer, Section, Position);

            Serializer.Sections[(uint)H3DSectionId.RawData].Values.Add(new RefValue()
            {
                Parent = this,
                Value = Data,
                Position = Position,
                Padding = 0x10,
            });

            return false;
        }
    }
}
