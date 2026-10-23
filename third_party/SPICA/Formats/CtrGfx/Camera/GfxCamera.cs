using SPICA.Formats.CtrH3D.Camera;
using SPICA.Serialization.Attributes;

namespace SPICA.Formats.CtrGfx.Camera
{
    [TypeChoice(0x4000000au, typeof(GfxCamera))]
    public class GfxCamera : GfxNodeTransform
    {
        public GfxCameraViewType ViewType;

        public GfxCameraProjectionType ProjectionType;

        public GfxCameraView View;

        public GfxCameraProjection Projection;

        public float WScale;

        public GfxCamera() 
        {
            ViewType = GfxCameraViewType.Rotate;
            ProjectionType = GfxCameraProjectionType.Perspective;
            WScale = 1F;
            View = new GfxCameraViewRotation();
            Projection = new GfxCameraProjectionPerspective();
        }

        public H3DCamera ToH3DCamera()
        {
            H3DCamera Output = new H3DCamera() { Name = Name };

            Output.TransformTranslation = TransformTranslation;
            Output.TransformRotation    = TransformRotation;
            Output.TransformScale       = TransformScale;

            Output.ViewType = (H3DCameraViewType)ViewType;

            switch (ProjectionType)
            {
                case GfxCameraProjectionType.Perspective:
                    Output.ProjectionType = H3DCameraProjectionType.Perspective;
                    break;
                case GfxCameraProjectionType.Frustum:
                case GfxCameraProjectionType.Orthogonal:
                    Output.ProjectionType = H3DCameraProjectionType.Orthogonal;
                    break;
            }

            Output.WScale = WScale;

            bool InheritUpRot       = false;
            bool InheritTargetRot   = false;
            bool InheritTargetTrans = false;

            if (View is GfxCameraViewAim ViewAim)
            {
                Output.View = new H3DCameraViewAim()
                {
                    Target = ViewAim.Target,
                    Twist  = ViewAim.Twist
                };

                InheritTargetRot   = (ViewAim.Flags & GfxCameraViewAimFlags.IsInheritingTargetRotation)    != 0;
                InheritTargetTrans = (ViewAim.Flags & GfxCameraViewAimFlags.IsInheritingTargetTranslation) != 0;
            }
            else if (View is GfxCameraViewLookAt ViewLookAt)
            {
                Output.View = new H3DCameraViewLookAt()
                {
                    Target   = ViewLookAt.Target,
                    UpVector = ViewLookAt.UpVector
                };

                InheritUpRot       = (ViewLookAt.Flags & GfxCameraViewLookAtFlags.IsInheritingUpRotation)        != 0;
                InheritTargetRot   = (ViewLookAt.Flags & GfxCameraViewLookAtFlags.IsInheritingTargetRotation)    != 0;
                InheritTargetTrans = (ViewLookAt.Flags & GfxCameraViewLookAtFlags.IsInheritingTargetTranslation) != 0;
            }
            else if (View is GfxCameraViewRotation ViewRotation)
            {
                Output.View = new H3DCameraViewRotation()
                {
                    Rotation = ViewRotation.Rotation
                };

                InheritTargetRot = ViewRotation.IsInheritingRotation;
            }

            if (Projection is GfxCameraProjectionPerspective ProjPersp)
            {
                Output.Projection = new H3DCameraProjectionPerspective()
                {
                    ZNear       = ProjPersp.ZNear,
                    ZFar        = ProjPersp.ZFar,
                    AspectRatio = ProjPersp.AspectRatio,
                    FOVY        = ProjPersp.FOVY
                };
            }
            else if (
                Projection is GfxCameraProjectionFrustum ||
                Projection is GfxCameraProjectionOrthogonal)
            {
                GfxCameraProjectionOrthogonal ProjOrtho = (GfxCameraProjectionOrthogonal)Projection;

                Output.Projection = new H3DCameraProjectionOrthogonal()
                {
                    ZNear       = ProjOrtho.ZNear,
                    ZFar        = ProjOrtho.ZFar,
                    AspectRatio = ProjOrtho.AspectRatio,
                    Height      = ProjOrtho.Height
                };
            }

            if (InheritUpRot)
                Output.Flags |= H3DCameraFlags.IsInheritingUpRotation;

            if (InheritTargetRot)
                Output.Flags |= H3DCameraFlags.IsInheritingTargetRotation;

            if (InheritTargetTrans)
                Output.Flags |= H3DCameraFlags.IsInheritingTargetTranslation;

            return Output;
        }

        public void FromH3D(H3DCamera camera)
        {
            this.TransformTranslation = camera.TransformTranslation;
            this.TransformRotation = camera.TransformRotation;
            this.TransformScale = camera.TransformScale;
            this.ViewType = (GfxCameraViewType)camera.ViewType;

            switch (camera.ProjectionType)
            {
                case H3DCameraProjectionType.Perspective:
                    this.ProjectionType = GfxCameraProjectionType.Perspective;
                    break;
                    //Todo
              /*  case H3DCameraProjectionType.Frustum:
                    this.ProjectionType = GfxCameraProjectionType.Frustum;
                    break;*/
                case H3DCameraProjectionType.Orthogonal:
                    this.ProjectionType = GfxCameraProjectionType.Orthogonal;
                    break;
            }
            this.WScale = camera.WScale;

            if (camera.View is H3DCameraViewAim ViewAim)
            {
                this.View = new GfxCameraViewAim()
                {
                    Target = ViewAim.Target,
                    Twist = ViewAim.Twist
                };
                if (camera.Flags.HasFlag(H3DCameraFlags.IsInheritingTargetTranslation))
                    ((GfxCameraViewAim)this.View).Flags = GfxCameraViewAimFlags.IsInheritingTargetTranslation;
                if (camera.Flags.HasFlag(H3DCameraFlags.IsInheritingTargetRotation))
                    ((GfxCameraViewAim)this.View).Flags = GfxCameraViewAimFlags.IsInheritingTargetRotation;
            }
            else if (camera.View is H3DCameraViewLookAt ViewLookAt)
            {
                this.View = new GfxCameraViewLookAt()
                {
                    Target = ViewLookAt.Target,
                    UpVector = ViewLookAt.UpVector,
                };
                if (camera.Flags.HasFlag(H3DCameraFlags.IsInheritingUpRotation))
                    ((GfxCameraViewLookAt)this.View).Flags = GfxCameraViewLookAtFlags.IsInheritingUpRotation;
                if (camera.Flags.HasFlag(H3DCameraFlags.IsInheritingTargetRotation))
                    ((GfxCameraViewLookAt)this.View).Flags = GfxCameraViewLookAtFlags.IsInheritingTargetRotation;
                if (camera.Flags.HasFlag(H3DCameraFlags.IsInheritingTargetTranslation))
                    ((GfxCameraViewLookAt)this.View).Flags = GfxCameraViewLookAtFlags.IsInheritingTargetTranslation;
            }
            else if (camera.View is H3DCameraViewRotation ViewRotation)
            {
                this.View = new GfxCameraViewRotation()
                {
                    Rotation = ViewRotation.Rotation,
                    IsInheritingRotation = camera.Flags.HasFlag(H3DCameraFlags.IsInheritingUpRotation),
                };
            }

            if (camera.Projection is H3DCameraProjectionPerspective ProjPersp)
            {
                this.Projection = new GfxCameraProjectionPerspective()
                {
                    ZNear = ProjPersp.ZNear,
                    ZFar = ProjPersp.ZFar,
                    AspectRatio = ProjPersp.AspectRatio,
                    FOVY = ProjPersp.FOVY
                };
            }
            else if (camera.Projection is H3DCameraProjectionOrthogonal)
            {
                H3DCameraProjectionOrthogonal ProjOrtho = (H3DCameraProjectionOrthogonal)camera.Projection;

                this.Projection = new GfxCameraProjectionOrthogonal()
                {
                    ZNear = ProjOrtho.ZNear,
                    ZFar = ProjOrtho.ZFar,
                    AspectRatio = ProjOrtho.AspectRatio,
                    Height = ProjOrtho.Height
                };
            }
        }
    }
}
