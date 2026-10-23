namespace SPICA.Formats.CtrH3D.Camera
{
    public class H3DCameraProjectionOrthogonal
    {
        public float ZNear;
        public float ZFar;
        public float AspectRatio;
        public float Height;

        public H3DCameraProjectionOrthogonal()
        {
            ZNear = 1.0f;
            ZFar = 10000.0f;
            AspectRatio = 1.667f;
            Height = 1f;
        }
    }
}
