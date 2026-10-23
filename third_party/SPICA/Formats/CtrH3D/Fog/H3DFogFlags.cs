using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace SPICA.Formats.CtrH3D.Fog
{
    [Flags]
    public enum H3DFogFlags : byte
    {
        ZFlip      = 1 << 0,
        HasDistanceAttenuation = 1 << 1
    }
}
