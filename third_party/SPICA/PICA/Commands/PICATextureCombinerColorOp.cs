using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace SPICA.PICA.Commands
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum PICATextureCombinerColorOp
    {
        Color = 0,
        OneMinusColor = 1,
        Alpha = 2,
        OneMinusAlpha = 3,
        Red = 4,
        OneMinusRed = 5,
        Green = 8,
        OneMinusGreen = 9,
        Blue = 12,
        OneMinusBlue = 13
    }
}
