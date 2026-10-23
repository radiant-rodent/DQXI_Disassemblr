using SPICA.Formats.Common;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Animation;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Serialization;

namespace SPICA.Formats.Xml
{
    public class H3DAnimationXML
    {
        public static void FromAnimation(H3DAnimation anim)
        {
            Animation an = new Animation();

            Header header= new Header();
            header.Name = anim.Name;
            header.AnimationType = anim.AnimationType;
            header.AnimationFlags = anim.AnimationFlags;
            an.Header = header;

            foreach (var elem in anim.Elements)
            {
                switch (elem.PrimitiveType)
                {
                    case H3DPrimitiveType.RGBA:
                        RGBAElement element = new RGBAElement();
                        element.Name = elem.Name;
                        header.Elements.Add(element);

                        for (int i = 0; i < anim.FramesCount; i++)
                        {
                            string[] keys = new string[4]; //rgba key values
                            var r = ((H3DAnimRGBA)elem.Content).R.KeyFrames.FirstOrDefault(x => (int)x.Frame == i);
                            var g = ((H3DAnimRGBA)elem.Content).G.KeyFrames.FirstOrDefault(x => (int)x.Frame == i);
                            var b = ((H3DAnimRGBA)elem.Content).B.KeyFrames.FirstOrDefault(x => (int)x.Frame == i);
                            var a = ((H3DAnimRGBA)elem.Content).A.KeyFrames.FirstOrDefault(x => (int)x.Frame == i);

                            if (((H3DAnimRGBA)elem.Content).R.KeyFrames.Any(x => (int)x.Frame == i)) keys[0] = r.Value.ToString();
                            if (((H3DAnimRGBA)elem.Content).G.KeyFrames.Any(x => (int)x.Frame == i)) keys[1] = g.Value.ToString();
                            if (((H3DAnimRGBA)elem.Content).B.KeyFrames.Any(x => (int)x.Frame == i)) keys[2] = b.Value.ToString();
                            if (((H3DAnimRGBA)elem.Content).A.KeyFrames.Any(x => (int)x.Frame == i)) keys[3] = a.Value.ToString();

                            if (keys.Any(x => !string.IsNullOrEmpty(x)))
                                element.KeyFrames.Add(new KeyFrame()
                                {
                                    Frame = i,
                                    Value = string.Join(',', keys),
                                });
                        }
                        //((H3DAnimRGBA)elem.Content).R.KeyFrames.Add();

                        break;
                }
            }

            XmlSerializer serializer = new XmlSerializer(typeof(Animation));
            TextWriter writer = new StreamWriter("test.xml");

            serializer.Serialize(writer, an);
            writer.Close();
        }
    }

    public class Animation
    {
        public FileSettings File = new FileSettings();
        public Header Header = new Header();
    }

    public class FileSettings
    {
        public string Version = "";
        public string Date = DateTime.Now.ToString("yyyy-MM-ddThh:mm:ss");
    }

    public class Header
    {
        [XmlAttribute]
        public string Name;

        [XmlAttribute]
        public H3DAnimationFlags AnimationFlags;

        [XmlAttribute]
        public float FramesCount;

        [XmlAttribute]
        public H3DAnimationType AnimationType;

        [XmlArrayItem(Type = typeof(RGBAElement))]
        public List<object> Elements = new List<object>();

        public MetaData MetaData;
    }

    public class RGBAElement
    {
        [XmlAttribute]
        public string Name;

        [XmlArrayItem]
        public List<KeyFrame> KeyFrames = new List<KeyFrame>();
    }

    public class KeyFrame
    {
        [XmlAttribute]
        public float Frame;
        [XmlAttribute]
        public string Value;
    }

    public class MetaData
    {

    }
}
