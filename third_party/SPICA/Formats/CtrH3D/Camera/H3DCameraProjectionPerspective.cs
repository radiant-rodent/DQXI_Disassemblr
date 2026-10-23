namespace SPICA.Formats.CtrH3D.Camera
{
    public class H3DCameraProjectionPerspective
    {
        public float ZNear;
        public float ZFar;
        public float AspectRatio;
        public float FOVY;

        public H3DCameraProjectionPerspective()
        {
            ZNear = 1.0f;
            ZFar = 10000.0f;
            AspectRatio = 1.667f;
            FOVY = 0.785398f;
        }
    }
}
