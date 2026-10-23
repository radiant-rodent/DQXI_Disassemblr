using SPICA.Formats.CtrH3D.Camera;
using SPICA.Serialization;
using SPICA.Serialization.Attributes;
using System.Collections.Generic;

namespace SPICA.Formats.CtrH3D.Animation
{
    public class H3DCameraAnim : H3DAnimation, ICustomSerialization
    {
        public H3DCameraViewType ViewType;
        public H3DCameraProjectionType ProjectionType;

        [Inline, FixedLength(10), Padding(4)]
        public sbyte[] ElementIndices;

        public H3DCameraAnim()
        {
            ElementIndices = new sbyte[10];
        }

        public H3DCameraAnim(H3DAnimation Anim) : this()
        {
            Name = Anim.Name;

            AnimationFlags = Anim.AnimationFlags;
            AnimationType  = Anim.AnimationType;

            CurvesCount = Anim.CurvesCount;

            FramesCount = Anim.FramesCount;

            Elements.AddRange(Anim.Elements);

            MetaData = Anim.MetaData;
        }

        public void Deserialize(BinaryDeserializer Deserializer)
        {
        }

        bool ICustomSerialization.Serialize(BinarySerializer Serializer)
        {
            ElementIndices = CalculateElementIndices();
            return false;
        }

        private sbyte[] CalculateElementIndices()
        {
            sbyte[] indices = new sbyte[10];
            for (int i = 0; i < indices.Length; i++)
                indices[i] = -1;

            for (int i = 0; i < this.Elements.Count; i++)
            {
                var type = (int)(this.Elements[i].TargetType - H3DTargetType.CameraTransform);
                indices[type] = (sbyte)i;
            }
            return indices;
        }
    }
}
