using SPICA.Math3D;
using SPICA.Serialization;
using SPICA.Serialization.Attributes;
using System.Collections.Generic;

namespace SPICA.Formats.CtrGfx.Animation
{
    public class GfxAnimMtxTransform : ICustomSerialization
    {
        [Ignore] public float StartFrame;
        [Ignore] public float EndFrame;

        [Ignore] public GfxLoopType PreRepeat;
        [Ignore] public GfxLoopType PostRepeat;

        [Ignore] private ushort Padding;

        [Ignore] public List<Matrix3x4> Frames;

        public GfxAnimMtxTransform()
        {
            Frames = new List<Matrix3x4>();
        }

        void ICustomSerialization.Deserialize(BinaryDeserializer Deserializer)
        {
            Deserializer.BaseStream.Seek(Deserializer.ReadPointer(), SeekOrigin.Begin);
            StartFrame = Deserializer.Reader.ReadSingle();
            EndFrame = Deserializer.Reader.ReadSingle();
            PreRepeat = (GfxLoopType)Deserializer.Reader.ReadByte();
            PostRepeat = (GfxLoopType)Deserializer.Reader.ReadByte();
            Padding = Deserializer.Reader.ReadUInt16();
            for (int i = 0; i < EndFrame - StartFrame + 2; i++)
                Frames.Add(Deserializer.Reader.ReadMatrix3x4());
        }

        bool ICustomSerialization.Serialize(BinarySerializer Serializer)
        {
            Serializer.Writer.Write(4); //offset
            Serializer.Writer.Write(StartFrame);
            Serializer.Writer.Write(EndFrame);
            Serializer.Writer.Write((byte)PreRepeat);
            Serializer.Writer.Write((byte)PostRepeat);
            Serializer.Writer.Write(Padding);
            for (int i = 0; i < Frames.Count; i++)
                Serializer.Writer.Write(Frames[i]);

            return true;
        }
    }
}
