using SPICA.Formats.Common;
using SPICA.Serialization.Attributes;

using System.Collections;
using System.Collections.Generic;
using System.Numerics;

namespace SPICA.Formats.CtrGfx
{
    public class GfxMetaDataSingle : GfxMetaData
    {
        [Inline] public List<float> Values = new List<float>();

        public GfxMetaDataSingle()
        {
            Type = GfxMetaDataType.Single;
        }
    }

    public class GfxMetaDataVector3 : GfxMetaData
    {
        [Inline] public List<Vector3> Values = new List<Vector3>();

        public GfxMetaDataVector3()
        {
            Type = GfxMetaDataType.Vector3;
        }
    }

    public class GfxMetaDataColor : GfxMetaData
    {
        [Inline] public List<Vector4> Values = new List<Vector4>();

        public GfxMetaDataColor()
        {
            Type = GfxMetaDataType.Color;
        }
    }

    public class GfxMetaDataInteger : GfxMetaData
    {
        [Inline] public List<int> Values = new List<int>();

        public GfxMetaDataInteger()
        {
            Type = GfxMetaDataType.Integer;
        }
    }

    public class GfxMetaDataString : GfxMetaData
    {
        public GfxStringFormat Format;

        [Inline]
        [TypeChoiceName("Format")]
        [TypeChoice((uint)GfxStringFormat.Ascii,   typeof(List<string>))]
        [TypeChoice((uint)GfxStringFormat.Utf8,    typeof(List<GfxStringUtf8>))]
        [TypeChoice((uint)GfxStringFormat.Utf16LE, typeof(List<GfxStringUtf16LE>))]
        [TypeChoice((uint)GfxStringFormat.Utf16BE, typeof(List<GfxStringUtf16BE>))]
        public IList Values;

        public GfxMetaDataString()
        {
            Values = new List<string>();
            Type = GfxMetaDataType.String;
        }
    }

    [TypeChoice(0x10000000u, typeof(GfxMetaDataString))]
    [TypeChoice(0x20000000u, typeof(GfxMetaDataInteger))]
    [TypeChoice(0x40000000u, typeof(GfxMetaDataColor))]
    [TypeChoice(0x80000000u, typeof(GfxMetaDataSingle))]
    public class GfxMetaData : INamed
    {
        private string _Name;

        public string Name
        {
            get => _Name;
            set => _Name = value ?? throw Exceptions.GetNullException("Name");
        }

        public GfxMetaDataType Type;

        public IList GetValue()
        {
            if (this is GfxMetaDataSingle) return ((GfxMetaDataSingle)this).Values;
            if (this is GfxMetaDataString) return ((GfxMetaDataString)this).Values;
            if (this is GfxMetaDataInteger) return ((GfxMetaDataInteger)this).Values;
            if (this is GfxMetaDataColor) return ((GfxMetaDataColor)this).Values;
            if (this is GfxMetaDataVector3) return ((GfxMetaDataVector3)this).Values;
            else return null;
        }

        public static GfxMetaData Create(GfxMetaDataType type, IList value)
        {
            switch (type)
            {
                case GfxMetaDataType.Single: return new GfxMetaDataSingle() { Values = (List<float>)value };
                case GfxMetaDataType.String: return new GfxMetaDataString() { Values = (List<string>)value };
                case GfxMetaDataType.Integer: return new GfxMetaDataInteger() { Values = (List<int>)value };
                case GfxMetaDataType.Color: return new GfxMetaDataColor() { Values = (List<Vector4>)value };
                case GfxMetaDataType.Vector3: return new GfxMetaDataVector3() { Values = (List<Vector3>)value };
                default:
                    return new GfxMetaDataString() { Values = (List<string>)value };
            }
        }
    }
}
