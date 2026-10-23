using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace SPICA.PICA.Commands
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum PICATextureCombinerAlphaOp
    {
        Alpha,
        OneMinusAlpha,
        Red,
        OneMinusRed,
        Green,
        OneMinusGreen,
        Blue,
        OneMinusBlue
    }
}
