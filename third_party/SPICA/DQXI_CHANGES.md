# Local changes to SPICA

SPICA (public domain, see LICENSE.txt) is vendored here as the reference BCH
reader for `tools/spica_ref`. Only `SPICA.csproj`'s library sources are kept.

Changes:

- `Formats/CtrH3D/Model/Mesh/H3DSubMesh.cs`: new `[Ignore] IndexBufferAddress`
  (file offset of the submesh index buffer), so manifests can key each draw by
  its vertex/index buffer offsets instead of its position in the draw list.
