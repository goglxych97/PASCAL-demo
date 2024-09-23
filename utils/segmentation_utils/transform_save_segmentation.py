# utils/segmentation_utils/transform_save_segmentation.py
from nibabel.orientations import io_orientation, ornt_transform, inv_ornt_aff
import nibabel as nib
import numpy as np


def save_transform_segmentation(
    segmentation_matrix, original_affine, original_header, file_path
):
    if not file_path.endswith(".nii.gz"):
        file_path += ".nii.gz"

    canonical_img = nib.Nifti1Image(segmentation_matrix, np.eye(4))
    ras_ornt = io_orientation(np.eye(4))
    original_ornt = io_orientation(original_affine)
    transform = ornt_transform(ras_ornt, original_ornt)

    transformed_data = nib.orientations.apply_orientation(
        canonical_img.get_fdata(), transform
    )

    new_affine = original_affine @ inv_ornt_aff(transform, segmentation_matrix.shape)
    u, s, vh = np.linalg.svd(new_affine[:3, :3])
    ortho_affine = u @ vh

    if np.linalg.det(ortho_affine) < 0:
        ortho_affine[:, -1] *= -1
    new_affine[:3, :3] = ortho_affine

    new_img = nib.Nifti1Image(transformed_data, new_affine, original_header)
    nib.save(new_img, file_path)
