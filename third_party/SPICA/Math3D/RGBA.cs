using System;
using System.IO;
using System.Numerics;

namespace SPICA.Math3D
{
    public struct RGBA
    {
        public byte R;
        public byte G;
        public byte B;
        public byte A;

        public static RGBA Black { get { return new RGBA(0, 0, 0, 255); } }

        public static RGBA White { get { return new RGBA(255, 255, 255, 255); } }

        public RGBA(byte R, byte G, byte B, byte A)
        {
            this.R = R;
            this.G = G;
            this.B = B;
            this.A = A;
        }

        public static RGBA FromFloat(Vector4 vec)
        {
            return new SPICA.Math3D.RGBA(
                                (byte)(vec.X * 255),
                                (byte)(vec.Y * 255),
                                (byte)(vec.Z * 255),
                                (byte)(vec.W * 255));
        }

        public static RGBA FromFloat(float R, float G, float B, float A)
        {
            return new SPICA.Math3D.RGBA(
                                (byte)(R * 255),
                                (byte)(G * 255),
                                (byte)(B * 255),
                                (byte)(A * 255));
        }

        public RGBA(uint Param)
        {
            R = (byte)(Param >>  0);
            G = (byte)(Param >>  8);
            B = (byte)(Param >> 16);
            A = (byte)(Param >> 24);
        }

        public RGBA(BinaryReader Reader)
        {
            R = Reader.ReadByte();
            G = Reader.ReadByte();
            B = Reader.ReadByte();
            A = Reader.ReadByte();
        }

        public override string ToString()
        {
            return $"R: {R} G: {G} B: {B} A: {A}";
        }

        public bool Equals(RGBA p)
        {
            // Optimization for a common success case.
            if (Object.ReferenceEquals(this, p))
            {
                return true;
            }

            // If run-time types are not exactly the same, return false.
            if (this.GetType() != p.GetType())
            {
                return false;
            }

            // Return true if the fields match.
            // Note that the base class is not invoked because it is
            // System.Object, which defines Equals as reference equality.
            return this.R == p.R &&
                   this.G == p.G &&
                   this.B == p.B &&
                   this.A == p.A;
        }

        public override bool Equals(object obj) => this.Equals((RGBA)obj);

        public override int GetHashCode() => (R, G, B, A).GetHashCode();

        public static bool operator ==(RGBA lhs, RGBA rhs)
        {
            return lhs.R == rhs.R &&
                    lhs.G == rhs.G &&
                    lhs.B == rhs.B &&
                    lhs.A == rhs.A;
        }

        public static bool operator !=(RGBA lhs, RGBA rhs) => !(lhs == rhs);

        public uint ToUInt32()
        {
            uint Param;

            Param  = (uint)R << 0;
            Param |= (uint)G << 8;
            Param |= (uint)B << 16;
            Param |= (uint)A << 24;

            return Param;
        }

        private const float ByteToFloat = 1f / 255;

        public Vector4 ToVector4()
        {
            return new Vector4(
                (float)Math.Round(R * ByteToFloat, 2),
                (float)Math.Round(G * ByteToFloat, 2),
                (float)Math.Round(B * ByteToFloat, 2),
                (float)Math.Round(A * ByteToFloat, 2));
        }

        public void Write(BinaryWriter Writer)
        {
            Writer.Write(R);
            Writer.Write(G);
            Writer.Write(B);
            Writer.Write(A);
        }
    }
}
