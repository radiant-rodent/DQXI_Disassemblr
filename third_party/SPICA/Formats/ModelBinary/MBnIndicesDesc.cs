using SPICA.Formats.Common;

using System.IO;

namespace SPICA.Formats.ModelBinary
{
    public class MBnIndicesDesc
    {
        public ushort[] BoneIndices;
        public ushort[] Indices;

        private uint PrimitivesCount;

        public MBnIndicesDesc() { }

        public MBnIndicesDesc(BinaryReader Reader, bool HasBuffer)
        {
            uint BoneIndicesCount = Reader.ReadUInt32();

            BoneIndices = new ushort[BoneIndicesCount];

            for (int Index = 0; Index < BoneIndicesCount; Index++)
            {
                BoneIndices[Index] = (ushort)Reader.ReadUInt32();
            }

            PrimitivesCount = Reader.ReadUInt32();

            if (HasBuffer)
            {
                ReadBuffer(Reader, false);
            }
        }

        public void ReadBuffer(BinaryReader Reader, bool NeedsAlign)
        {
            if (NeedsAlign)
            {
                Reader.Align(0x20);
            }

            Indices = new ushort[PrimitivesCount];

            for (int Index = 0; Index < PrimitivesCount; Index++)
            {
                Indices[Index] = Reader.ReadUInt16();
            }

            Reader.Align(4);
        }

        public void Write(BinaryWriter Writer, bool HasBuffer)
        {
            Writer.Write(BoneIndices.Length);
            for (int Index = 0; Index < BoneIndices.Length; Index++)
                Writer.Write((uint)BoneIndices[Index]);
            Writer.Write(Indices.Length);

            if (HasBuffer)
                WriteBuffer(Writer, false);
        }

        public void WriteBuffer(BinaryWriter Writer, bool NeedsAlign)
        {
            if (NeedsAlign)
            {
                Writer.Align(0x20, 0xFF);
            }

            for (int Index = 0; Index < Indices.Length; Index++)
                Writer.Write(Indices[Index]);

            Writer.Align(4, 0xFF);
        }
    }
}
