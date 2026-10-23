using SPICA.Formats.Common;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Model;
using SPICA.Formats.CtrH3D.Model.Mesh;
using SPICA.PICA.Commands;

using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;

namespace SPICA.Formats.ModelBinary
{
    public class MBn
    {
        public ushort Type;

        private uint MeshFlags;
        private uint VertexFlags;
        private int MeshesCount;

        public readonly List<MBnIndicesDesc>  IndicesDesc;
        public readonly List<MBnVerticesDesc> VerticesDesc;

        public H3D BaseScene;

        public MBn()
        {
            IndicesDesc  = new List<MBnIndicesDesc>();
            VerticesDesc = new List<MBnVerticesDesc>();
        }

        public void Save(string filePath)
        {
            using (var FS = new FileStream(filePath, FileMode.Create, FileAccess.Write)) {
                Save(FS);
            }
        }

        public void Save(Stream stream)
        {
            Write(new BinaryWriter(stream));
        }

        public MBn(string filePath, H3D BaseScene) : this()
        {
            using (var FS = new FileStream(filePath, FileMode.Open, FileAccess.Read)) {
                Read(new BinaryReader(FS), BaseScene);
            }
        }

        public MBn(BinaryReader Reader, H3D BaseScene) : this() {
            Read(Reader, BaseScene);
        }

        private void Read(BinaryReader Reader, H3D BaseScene)
        {
            this.BaseScene = BaseScene;

            Type = (ushort)Reader.ReadUInt32();

            MeshFlags   = Reader.ReadUInt32();
            VertexFlags = Reader.ReadUInt32();
            MeshesCount = Reader.ReadInt32();

            bool HasSingleVerticesDesc = (VertexFlags & 1) != 0;
            bool HasBuiltInDataBuffer = Type == 4;

            if (HasSingleVerticesDesc)
            {
                /*
                 * This is used when all meshes inside the file uses the same vertex format.
                 * This save some file space by only storing this information once.
                 * In this case the file will have only one big vertex buffer at the beggining,
                 * and all meshes will use that buffer.
                 */
                VerticesDesc.Add(new MBnVerticesDesc(Reader, MeshesCount, HasBuiltInDataBuffer));
            }

            for (int i = 0; i < MeshesCount; i++)
            {
                int SubMeshesCount = Reader.ReadInt32();

                for (int j = 0; j < SubMeshesCount; j++)
                {
                    IndicesDesc.Add(new MBnIndicesDesc(Reader, HasBuiltInDataBuffer));
                }

                if (!HasSingleVerticesDesc)
                {
                    VerticesDesc.Add(new MBnVerticesDesc(Reader, SubMeshesCount, HasBuiltInDataBuffer));
                }
            }

            if (HasSingleVerticesDesc)
            {
                //This is used when the model only have one vertex buffer at the beggining.
                for (int i = 0; i < IndicesDesc.Count; i++)
                {
                    if (i == 0 && !HasBuiltInDataBuffer)
                        VerticesDesc[0].ReadBuffer(Reader, true);
                    else if (i > 0)
                        VerticesDesc.Add(VerticesDesc[0]);

                    if (!HasBuiltInDataBuffer)
                    {
                        IndicesDesc[i].ReadBuffer(Reader, true);
                    }
                }
            }
            else if (!HasBuiltInDataBuffer)
            {
                //This is used when the file have various vertex/index buffer after the descriptors.
                int IndicesIndex = 0;

                for (int i = 0; i < MeshesCount; i++)
                {
                    VerticesDesc[i].ReadBuffer(Reader, true);

                    for (int j = 0; j < VerticesDesc[i].SubMeshesCount; j++)
                    {
                        IndicesDesc[IndicesIndex++].ReadBuffer(Reader, true);
                    }
                }
            }
        }

        private void Write(BinaryWriter Writer)
        {
            Writer.Write((ushort)Type);
            Writer.Write((ushort)0xFFFF);
            Writer.Write(MeshFlags);
            Writer.Write(VertexFlags);
            Writer.Write(MeshesCount);

            bool HasSingleVerticesDesc = (VertexFlags & 1) != 0;
            bool HasBuiltInDataBuffer = Type == 4;

            if (HasSingleVerticesDesc)
            {
                /*
                 * This is used when all meshes inside the file uses the same vertex format.
                 * This save some file space by only storing this information once.
                 * In this case the file will have only one big vertex buffer at the beggining,
                 * and all meshes will use that buffer.
                 */
                VerticesDesc[0].Write(Writer, HasBuiltInDataBuffer);
            }

            int id = 0;
            for (int i = 0; i < MeshesCount; i++)
            {
                //Sub mesh count
                int subMeshCount = HasSingleVerticesDesc ? 1 : VerticesDesc[i].SubMeshesCount; 
                Writer.Write(subMeshCount);
                for (int j = 0; j < subMeshCount; j++)
                    IndicesDesc[id++].Write(Writer, HasBuiltInDataBuffer);

                if (!HasSingleVerticesDesc)
                    VerticesDesc[i].Write(Writer, HasBuiltInDataBuffer);
            }

            if (HasSingleVerticesDesc)
            {
                //This is used when the model only have one vertex buffer at the beggining.
                for (int i = 0; i < IndicesDesc.Count; i++)
                {
                    if (i == 0 && !HasBuiltInDataBuffer)
                        VerticesDesc[0].WriteBuffer(Writer, true);
                    else if (i > 0)
                        VerticesDesc.Add(VerticesDesc[0]);

                    if (!HasBuiltInDataBuffer)
                        IndicesDesc[i].WriteBuffer(Writer, true);
                }
            }
            else if (!HasBuiltInDataBuffer)
            {
                //This is used when the file have various vertex/index buffer after the descriptors.
                int IndicesIndex = 0;

                for (int i = 0; i < MeshesCount; i++)
                {
                    VerticesDesc[i].WriteBuffer(Writer, true);

                    for (int j = 0; j < VerticesDesc[i].SubMeshesCount; j++)
                        IndicesDesc[IndicesIndex++].WriteBuffer(Writer, true);
                }
            }
            Writer.Align(16, 0xFF);
        }

        public void FromH3D(H3DModel Model)
        {
            VerticesDesc.Clear();
            IndicesDesc.Clear();
            MeshesCount = Model.Meshes.Count;

            //Check for same attributes used
            var attributeList = Model.Meshes.Select(x => string.Join("", x.Attributes.Select(x => x.ToString()))).Distinct().ToList();
            var sameBuffers = Model.Meshes.All(x => x.RawBuffer.Length == Model.Meshes[0].RawBuffer.Length);

            bool HasSingleVerticesDesc = attributeList.Count == 1 && sameBuffers;

            VertexFlags = (uint)(HasSingleVerticesDesc ? 1 : 0);
            MeshFlags = 0; //No idea what these do

            int shapeID = 0;
            foreach (var mesh in Model.Meshes)
            {
                if (!mesh.MetaData.Contains("ShapeId"))
                    mesh.MetaData.Add(new H3DMetaDataValue("ShapeId", new int[] { shapeID++ }));

                //Indices desciptors per sub mesh
                for (int j = 0; j < mesh.SubMeshes.Count; j++)
                {
                    IndicesDesc.Add(new MBnIndicesDesc()
                    {
                        BoneIndices = mesh.SubMeshes[j].BoneIndices.Take(mesh.SubMeshes[j].BoneIndicesCount).ToArray(),
                        Indices = mesh.SubMeshes[j].Indices,
                    });
                }
                //Add vertex info per mesh or only once depending on flags
                if (!HasSingleVerticesDesc || HasSingleVerticesDesc && VerticesDesc.Count == 0)
                {
                    var vertexDesc = new MBnVerticesDesc();
                    vertexDesc.Attributes = mesh.Attributes;
                    vertexDesc.SubMeshesCount = mesh.SubMeshes.Count;
                    vertexDesc.RawBuffer = mesh.RawBuffer;
                    vertexDesc.VertexStride = mesh.VertexStride;
                    VerticesDesc.Add(vertexDesc);
                }
            }
        }

        public H3D ToH3D()
        {
            H3D Output = BaseScene;

            H3DModel Model = Output.Models[0];

            int IndicesIndex = 0, i = 0;

            foreach (H3DMesh Mesh in Model.Meshes.OrderBy(x => (int)x.MetaData["ShapeId"].Values[0]))
            {
                Mesh.PositionOffset = Vector4.Zero;

                Mesh.Attributes.Clear();
                Mesh.Attributes.AddRange(VerticesDesc[i].Attributes);

                Mesh.RawBuffer    = VerticesDesc[i].RawBuffer;
                Mesh.VertexStride = VerticesDesc[i].VertexStride;

                for (int j = 0; j < Mesh.SubMeshes.Count; j++)
                {
                    H3DSubMesh SM = Mesh.SubMeshes[j];

                    SM.Indices     = IndicesDesc[IndicesIndex].Indices;
                    SM.BoneIndices = IndicesDesc[IndicesIndex].BoneIndices;

                    IndicesIndex++;
                }

                i++;
            }

            return Output;
        }
    }
}
