using SPICA.Formats.CtrGfx.Model.Material;
using SPICA.Math3D;

namespace SPICA.PICA.Commands
{
    public class PICATexEnvStage
    {
        public PICATexEnvSource   Source;
        public PICATexEnvOperand  Operand;
        public PICATexEnvCombiner Combiner;
        public RGBA               Color;
        public PICATexEnvScale    Scale;

        public bool UpdateColorBuffer;
        public bool UpdateAlphaBuffer;

        public GfxTexEnvConstant Constant;

        public bool IsColorPassThrough
        {
            get
            {
                return
                    Combiner.Color   == PICATextureCombinerMode.Replace    &&
                    Source.Color[0]  == PICATextureCombinerSource.Previous &&
                    Operand.Color[0] == PICATextureCombinerColorOp.Color   &&
                    Scale.Color      == PICATextureCombinerScale.One       &&
                    !UpdateColorBuffer;
            }
        }

        public bool IsAlphaPassThrough
        {
            get
            {
                return
                    Combiner.Alpha   == PICATextureCombinerMode.Replace    &&
                    Source.Alpha[0]  == PICATextureCombinerSource.Previous &&
                    Operand.Alpha[0] == PICATextureCombinerAlphaOp.Alpha   &&
                    Scale.Alpha      == PICATextureCombinerScale.One       &&
                    !UpdateAlphaBuffer;
            }
        }

        public static PICATexEnvStage Texture0
        {
            get
            {
                //Does TextureRGB * SecondaryColor, and TextureA is used unmodified
                //Note: This is meant to be used on the first stage
                PICATexEnvStage Output = new PICATexEnvStage();

                Output.Source.Color[0] = PICATextureCombinerSource.Texture0;
                Output.Source.Alpha[0] = PICATextureCombinerSource.Texture0;

                return Output;
            }
        }

        public static PICATexEnvStage VertexColor
        {
            get
            {
                //Does TextureRGB * SecondaryColor, and TextureA is used unmodified
                //Note: This is meant to be used on the first stage
                PICATexEnvStage Output = new PICATexEnvStage();

                Output.Source.Color[0] = PICATextureCombinerSource.PrimaryColor;
                Output.Source.Alpha[0] = PICATextureCombinerSource.PrimaryColor;

                return Output;
            }
        }

        public static PICATexEnvStage PassThrough
        {
            get
            {
                //Does nothing, just pass the previous color down the pipeline
                PICATexEnvStage Output = new PICATexEnvStage();

                Output.Source.Color[0] = PICATextureCombinerSource.Previous;
                Output.Source.Alpha[0] = PICATextureCombinerSource.Previous;

                return Output;
            }
        }

        public static PICATexEnvStage PassThrough2
        {
            get
            {
                return new PICATexEnvStage()
                {
                    Source = new PICATexEnvSource()
                    {
                        Color = new PICATextureCombinerSource[3]
               {
                           PICATextureCombinerSource.Previous,
                           PICATextureCombinerSource.FragmentPrimaryColor,
                           PICATextureCombinerSource.Constant,
               },
                        Alpha = new PICATextureCombinerSource[3]
               {
                         PICATextureCombinerSource.Previous,
                           PICATextureCombinerSource.FragmentPrimaryColor,
                           PICATextureCombinerSource.Constant,
               },
                    },
                    Operand = new PICATexEnvOperand()
                    {
                        Color = new PICATextureCombinerColorOp[3]
               {
                           PICATextureCombinerColorOp.Color,
                           PICATextureCombinerColorOp.Color,
                           PICATextureCombinerColorOp.Color,
               },
                        Alpha = new PICATextureCombinerAlphaOp[3]
               {
                           PICATextureCombinerAlphaOp.Alpha,
                           PICATextureCombinerAlphaOp.Alpha,
                           PICATextureCombinerAlphaOp.Alpha,
               },
                    },
                    Combiner = new PICATexEnvCombiner()
                    {
                        Color = PICATextureCombinerMode.Replace,
                        Alpha = PICATextureCombinerMode.Replace,
                    },
                    Scale = new PICATexEnvScale()
                    {
                        Color = PICATextureCombinerScale.One,
                        Alpha = PICATextureCombinerScale.One,
                    },
                    Color = new RGBA(0, 0, 0, 255),
                    UpdateAlphaBuffer = false,
                    UpdateColorBuffer = false,
                };
            }
        }

        public PICATexEnvStage()
        {
            Source   = new PICATexEnvSource();
            Operand  = new PICATexEnvOperand();
            Combiner = new PICATexEnvCombiner();
            Color    = new RGBA();
            Scale    = new PICATexEnvScale();
        }

        public static void SetUpdateBuffer(PICATexEnvStage[] TexEnvStages, uint Param)
        {
            TexEnvStages[1].UpdateColorBuffer = (Param & 0x100)  != 0;
            TexEnvStages[2].UpdateColorBuffer = (Param & 0x200)  != 0;
            TexEnvStages[3].UpdateColorBuffer = (Param & 0x400)  != 0;
            TexEnvStages[4].UpdateColorBuffer = (Param & 0x800)  != 0;

            TexEnvStages[1].UpdateAlphaBuffer = (Param & 0x1000) != 0;
            TexEnvStages[2].UpdateAlphaBuffer = (Param & 0x2000) != 0;
            TexEnvStages[3].UpdateAlphaBuffer = (Param & 0x4000) != 0;
            TexEnvStages[4].UpdateAlphaBuffer = (Param & 0x8000) != 0;
        }

        public static uint GetUpdateBuffer(PICATexEnvStage[] TexEnvStages)
        {
            uint Param = 0;

            if (TexEnvStages[1].UpdateColorBuffer) Param |= 0x100;
            if (TexEnvStages[2].UpdateColorBuffer) Param |= 0x200;
            if (TexEnvStages[3].UpdateColorBuffer) Param |= 0x400;
            if (TexEnvStages[4].UpdateColorBuffer) Param |= 0x800;

            if (TexEnvStages[1].UpdateAlphaBuffer) Param |= 0x1000;
            if (TexEnvStages[2].UpdateAlphaBuffer) Param |= 0x2000;
            if (TexEnvStages[3].UpdateAlphaBuffer) Param |= 0x4000;
            if (TexEnvStages[4].UpdateAlphaBuffer) Param |= 0x8000;

            return Param;
        }
    }
}
