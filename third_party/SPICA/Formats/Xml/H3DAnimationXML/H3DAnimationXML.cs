using SPICA.Formats.Common;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Animation;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace SPICA.Formats.XML
{
    internal class H3DAnimationXML
    {
        public void FromAnimation(H3DAnimation anim)
        {

        }
    }

    public class Header
    {
        public string Name;

        public H3DAnimationFlags AnimationFlags;
        public H3DAnimationType AnimationType;

        public float FramesCount;

        public List<Element> Elements = new List<Element>();

        public MetaData MetaData;
    }

    public class Element
    {

    }

    public class MetaData
    {

    }
}
