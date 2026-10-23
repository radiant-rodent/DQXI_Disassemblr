using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace SPICA.PICA.Commands
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum PICATestFunc
    {
        Never,
        Always,
        Equal,
        Notequal,
        Less,
        Lequal,
        Greater,
        Gequal
    }
}
