namespace SPICA.Formats.CtrGfx.Camera
{
    public class GfxCameraProjectionPerspective : GfxCameraProjection
    {
        public float AspectRatio;
        public float FOVY;

        public GfxCameraProjectionPerspective()
        {
            this.AspectRatio = 1.0f;
            this.FOVY = 0.3f;
            this.ZNear = 1f;
            this.ZFar = 100000;
        }
    }
}
