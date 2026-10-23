using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace SPICA.PICA.Commands
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum PICATextureCombinerScale
    {
        One,
        Two,
        Four
    }
}
