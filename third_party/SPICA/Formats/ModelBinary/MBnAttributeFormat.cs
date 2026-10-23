using SPICA.PICA.Commands;

using System;

namespace SPICA.Formats.ModelBinary
{
    public enum MBnAttributeFormat
    {
        Float,
        Ubyte,
        Byte,
        Short
    }

    public static class MBnAttributeFormatExtensions
    {
        public static PICAAttributeFormat ToPICAAttributeFormat(this MBnAttributeFormat AttrFmt)
        {
            switch (AttrFmt)
            {
                case MBnAttributeFormat.Float: return PICAAttributeFormat.Float;
                case MBnAttributeFormat.Ubyte: return PICAAttributeFormat.Ubyte;
                case MBnAttributeFormat.Byte:  return PICAAttributeFormat.Byte;
                case MBnAttributeFormat.Short: return PICAAttributeFormat.Short;

                default: throw new ArgumentException($"Invalid MBn Attribute format {AttrFmt}!");
            }
        }
        public static MBnAttributeFormat ToMbnAttributeFormat(this PICAAttributeFormat AttrFmt)
        {
            switch (AttrFmt)
            {
                case PICAAttributeFormat.Float: return MBnAttributeFormat.Float;
                case PICAAttributeFormat.Ubyte: return MBnAttributeFormat.Ubyte;
                case PICAAttributeFormat.Byte: return MBnAttributeFormat.Byte;
                case PICAAttributeFormat.Short: return MBnAttributeFormat.Short;

                default: throw new ArgumentException($"Invalid MBn Attribute format {AttrFmt}!");
            }
        }
    }
}
