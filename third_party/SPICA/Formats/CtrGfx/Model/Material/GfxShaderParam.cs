using Newtonsoft.Json;
using SPICA.Serialization;
using SPICA.Serialization.Attributes;

namespace SPICA.Formats.CtrGfx.Model.Material
{
    [JsonObject(ItemTypeNameHandling = TypeNameHandling.All)]
    public class GfxShaderParam : ICustomSerialization
    {
        public string Name;
        public int Index;
        public ParamType Type;

        [Ignore]
        public object Value;

        void ICustomSerialization.Deserialize(BinaryDeserializer Deserializer) {

            switch (Type)
            {
                case ParamType.Boolean: 
                    Value = new bool[1] { Deserializer.Reader.ReadUInt32() == 1 };
                    break;
                case ParamType.Float:
                    Value = new float[1] { Deserializer.Reader.ReadSingle() };
                    break;
                case ParamType.Float2:
                    Value = new float[2]
                     {
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle()
                      };
                    break;
                case ParamType.Float3:
                    Value = new float[3]
                     {
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle(),
                      };
                    break;
                case ParamType.Float4:
                    Value = new float[4]
                     {
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle(),
                       Deserializer.Reader.ReadSingle(),
                      };
                    break;
                default:
                    throw new Exception($"Unknown type {Type}");
            }
        }

        bool ICustomSerialization.Serialize(BinarySerializer Serializer)
        {
            var pos = Serializer.Writer.BaseStream.Position;
            Serializer.BaseStream.Seek(pos + 12, SeekOrigin.Begin);

            switch (Type)
            {
                case ParamType.Boolean:
                    uint v = (uint)(((bool[])Value)[0] ? 1 : 0);
                    Serializer.Writer.Write(v);
                    break;
                case ParamType.Float:
                case ParamType.Float2:
                case ParamType.Float3:
                case ParamType.Float4:
                    for (int i = 0; i < ((float[])Value).Length; i++)
                        Serializer.Writer.Write(((float[])Value)[i]);
                    break;
                default:
                    throw new Exception($"Unknown type {Type}");
            }
            Serializer.BaseStream.Seek(pos, SeekOrigin.Begin);

            return false;
        }

        public enum ParamType : uint
        {
            Boolean, Float, Float2, Float3, Float4,
        }
    }
}
