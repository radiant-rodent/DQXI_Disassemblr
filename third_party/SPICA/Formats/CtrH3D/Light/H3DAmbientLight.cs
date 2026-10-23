using SPICA.Math3D;

namespace SPICA.Formats.CtrH3D.Light
{
    public class H3DAmbientLight
    {
        public RGBA Color;

        public H3DAmbientLight()
        {
            Color = new RGBA(128, 128, 128, 255);
        }
    }
}
