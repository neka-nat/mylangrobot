import cv2
import numpy as np
import supervision as sv
import torch
from segment_anything import SamAutomaticMaskGenerator, sam_model_registry

from .utils import download_sam_model_to_cache


class Annotator:
    MIN_AREA_PERCENTAGE = 0.005
    MAX_AREA_PERCENTAGE = 0.05

    def __init__(self, device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu")):
        sam = sam_model_registry["vit_h"](checkpoint=download_sam_model_to_cache("mylangrobot")).to(device=device)
        self.mask_generator = SamAutomaticMaskGenerator(sam)

    def get_annotated_image(self, image: np.ndarray, opacity: float = 0.3) -> tuple[np.ndarray, sv.Detections]:
        """Get annotated image and detections from image.

        Note: The input image should be in BGR format. The returned image is in RGB format.
        """
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        sam_result = self.mask_generator.generate(image_rgb)
        detections = sv.Detections.from_sam(sam_result=sam_result)
        height, width, _ = image.shape
        image_area = height * width

        min_area_mask = (detections.area / image_area) > self.MIN_AREA_PERCENTAGE
        max_area_mask = (detections.area / image_area) < self.MAX_AREA_PERCENTAGE
        detections = detections[min_area_mask & max_area_mask]

        # setup annotators
        mask_annotator = sv.MaskAnnotator(color_lookup=sv.ColorLookup.INDEX, opacity=opacity)
        label_annotator = sv.LabelAnnotator(
            color_lookup=sv.ColorLookup.INDEX,
            text_position=sv.Position.CENTER,
            text_scale=0.5,
            text_color=sv.Color.white(),
            color=sv.Color.black(),
            text_thickness=1,
            text_padding=2,
        )

        # annotate
        labels = [str(i) for i in range(len(detections))]
        annotated_image = mask_annotator.annotate(scene=image_rgb.copy(), detections=detections)
        annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)
        return annotated_image, detections
