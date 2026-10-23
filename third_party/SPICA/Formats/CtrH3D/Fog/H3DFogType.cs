using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace SPICA.Formats.CtrH3D.Fog
{
    [Flags]
    public enum H3DFogType : byte
    {
        Linear,
        Exponent,
        Exponent_Square,
        Proper_Exponent,
        Proper_Exponent_Square
    }
}
