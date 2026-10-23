using System.Numerics;

namespace SPICA.Formats.CtrH3D.Light
{
    public class H3DHemisphereLight
    {
        public Vector4 GroundColor;
        public Vector4 SkyColor;

        public Vector3 Direction;

        public float LerpFactor;

        public H3DHemisphereLight()
        {
            SkyColor = new Vector4(0.3f, 0.55f, 0.9f, 1);
            GroundColor = new Vector4(0.5f, 0.38f, 0.2313f, 1);
            Direction = new Vector3(0, 1, 0);
            LerpFactor = 0.5f;
        }
    }
}
