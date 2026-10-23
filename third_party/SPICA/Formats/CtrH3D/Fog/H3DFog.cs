using SPICA.Formats.Common;
using SPICA.Math3D;
using SPICA.Serialization.Attributes;
using System.Numerics;

namespace SPICA.Formats.CtrH3D.Fog
{
    public class H3DFog : INamed
    {
        private string _Name;

        public string Name
        {
            get => _Name;
            set => _Name = value ?? throw Exceptions.GetNullException("Name");
        }

        public Vector3 TransformScale;
        public Vector3 TransformRotation;
        public Vector3 TransformTranslation;

        public H3DFogType Type;
        [Padding(4)]public H3DFogFlags Flags;

        public RGBA Color;
        public float MinDepth;
        public float MaxDepth;
        public float Density;

        public H3DMetaData MetaData;

        public H3DFog()
        {
            Type = H3DFogType.Linear;
            Color = new RGBA(128, 128, 255, 255);
            Density = 1f;
            MinDepth = 1000;
            MaxDepth = 1000000;
        }
    }
}
