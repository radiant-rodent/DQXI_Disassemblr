using System.Numerics;

namespace SPICA.Formats.CtrGfx.Light
{
    public class GfxVertexLight : GfxLight
    {
        public GfxLightType Type;

        public Vector4 AmbientColor;
        public Vector4 DiffuseColor;

        public Vector3 Direction;

        public float AttenuationConstant;
        public float AttenuationLinear;
        public float AttenuationQuadratic;
        public float AttenuationEnabled;

        public float SpotExponent;
        public float SpotCutOffAngle;

        public GfxVertexLightFlags Flags;

        public GfxVertexLight()
        {
            DiffuseColor = Vector4.One;
            AmbientColor = new Vector4(0, 0,0, 1f);
            Direction = new Vector3(0, -1f, 0);
            AttenuationConstant = 1F;
            SpotExponent = 1f;
            SpotCutOffAngle = 1.571f;
        }
    }
}
