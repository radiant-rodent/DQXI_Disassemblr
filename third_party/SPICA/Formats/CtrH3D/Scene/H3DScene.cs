using SPICA.Formats.Common;
using SPICA.Formats.CtrH3D.LUT;
using SPICA.Serialization.Attributes;
using System.Collections.Generic;

namespace SPICA.Formats.CtrH3D.Scene
{
    public class H3DScene : INamed
    {
        private string _Name;

        public string Name
        {
            get => _Name;
            set => _Name = value ?? throw Exceptions.GetNullException("Name");
        }

        public List<IndexedName> Cameras;
        public List<IndexedNameArray> LightSets;
        public List<IndexedName> Fogs;

        public H3DMetaData MetaData;

        public H3DScene()
        {
            Cameras = new List<IndexedName>();
            LightSets = new List<IndexedNameArray>();
            Fogs = new List<IndexedName>();
        }
    }

    [Inline]
    public class IndexedNameArray
    {
        public int Index;

        public List<string> Names;

        public IndexedNameArray()
        {
            Names = new List<string>();
        }
    }

    [Inline]
    public class IndexedName : INamed
    {
        public int Index;

        private string _Name;
        public string Name
        {
            get => _Name;
            set => _Name = value ?? throw Exceptions.GetNullException("Name");
        }
    }
}
