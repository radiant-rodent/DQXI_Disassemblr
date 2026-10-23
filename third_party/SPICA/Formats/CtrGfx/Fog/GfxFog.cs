using SPICA.Formats.Common;
using SPICA.Formats.CtrH3D.Fog;
using SPICA.Math3D;
using SPICA.Serialization.Attributes;
using System;

namespace SPICA.Formats.CtrGfx.Fog
{
    [TypeChoice(0x40000042, typeof(GfxFog))]
    public class GfxFog : GfxNodeTransform
    {
        public float ColorR;
        public float ColorG;
        public float ColorB;

        public float Padding;

        public GfxFogBuffer FogBuffer; //?
        public GfxFogData Data;

        public GfxFog()
        {
            Data = new GfxFogData();
            FogBuffer = new GfxFogBuffer();
            ColorR = 0.5f;
            ColorG = 0.5f;
            ColorB = 1f;
        }

        public H3DFog ToH3D()
        {
            H3DFogType type = H3DFogType.Linear;

            if (this.Data.Type == 1) type = H3DFogType.Linear;
            if (this.Data.Type == 2) type = H3DFogType.Exponent;
            if (this.Data.Type == 3) type = H3DFogType.Exponent_Square;

            return new H3DFog()
            {
                Name = this.Name,
                TransformTranslation = this.TransformTranslation,
                TransformRotation = this.TransformRotation,
                TransformScale = this.TransformScale,
                Color = RGBA.FromFloat(ColorR, ColorG, ColorB, 1f),
                Density = Data.Density,
                MinDepth = Data.Near,
                MaxDepth = Data.Far,
                Type = type,
            };
        }

        public void FromH3D(H3DFog fog)
        {
            Name = fog.Name;
            TransformTranslation = fog.TransformTranslation;
            TransformRotation = fog.TransformRotation;
            TransformScale = fog.TransformScale;
            ColorR = fog.Color.R / 255f;
            ColorG = fog.Color.G / 255f;
            ColorB = fog.Color.B / 255f;
            Data.Near = (uint)fog.MinDepth;
            Data.Far = (uint)fog.MaxDepth;
            Data.Density = fog.Density;
            Data.Type = 1;
            switch (fog.Type)
            {
                case H3DFogType.Proper_Exponent_Square:
                case H3DFogType.Exponent_Square:
                    this.Data.Type = 3;
                    break;
                case H3DFogType.Proper_Exponent:
                case H3DFogType.Exponent:
                    this.Data.Type = 2;
                    break;
                case H3DFogType.Linear:
                    this.Data.Type = 1;
                    break;
            }
        }
    }

    public class GfxFogBuffer
    {
        [Inline, FixedLength(137)]
        public uint[] Unk;

        public GfxFogBuffer()
        {
            Unk = new uint[137];

            Unk[0] = 2147483648; //00 00 00 80 magic maybe
            Unk[3] = 528; //offset?
            Unk[4] = 4; //count?
            Unk[6] = 983270;  //E6 00 0F 00
            Unk[8] = 134152424; //E8 00 FF 07
            //rest of data is all 0s
        }
    }

    public class GfxFogData
    {
        public uint Type;
        public float Near;
        public float Far;
        public float Density;

        public GfxFogData()
        {
            Type = 1;
            Near = 1000;
            Far = 1000000;
            Density = 1.0f;
        }
    }
}
