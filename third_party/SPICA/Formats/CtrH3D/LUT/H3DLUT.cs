using SPICA.Formats.Common;

using System.Collections.Generic;

namespace SPICA.Formats.CtrH3D.LUT
{
    public class H3DLUT : INamed
    {
        public readonly List<H3DLUTSampler> Samplers;

        private string _Name;

        public string Name
        {
            get => _Name;
            set => _Name = value ?? throw Exceptions.GetNullException("Name");
        }

        public H3DLUT()
        {
            Samplers = new List<H3DLUTSampler>();
        }

        public void Export(string filePath)
        {
            H3D h3d = new H3D();
            h3d.LUTs.Add(this);
            H3D.Save(filePath, h3d);
        }

        public void Replace(string filePath)
        {
            H3D h3d = H3D.Open(File.ReadAllBytes(filePath));
            if (h3d.LUTs.Count == 0)
                return;

            var lut = h3d.LUTs[0];
            this.Name = lut.Name;

            this.Samplers.Clear();
            foreach (var sampler in lut.Samplers)
                this.Samplers.Add(sampler); 
        }
    }
}
