from collections import defaultdict

import cv2
import numpy as np

from ..pipeline.evidence import MANIPULATION, finding, location


def inspect(image, doc, page):
    im = image.convert("L")
    im.thumbnail((1100, 1100))
    keypoints, descriptors = cv2.ORB_create(nfeatures=700).detectAndCompute(np.asarray(im), None)
    if descriptors is None or len(descriptors) < 5:
        return []
    clusters = defaultdict(list)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    for pair in matcher.knnMatch(descriptors, descriptors, k=4):
        for match in pair:
            if match.trainIdx <= match.queryIdx or match.distance > 9:
                continue
            a, b = (keypoints[index].pt for index in (match.queryIdx, match.trainIdx))
            dx, dy = b[0]-a[0], b[1]-a[1]
            if dx*dx+dy*dy > 70**2:
                clusters[(round(dx/8), round(dy/8))].append((a, b))
    pairs = max(clusters.values(), key=len, default=[])
    if len(pairs) < 12:
        return []
    def box(points):
        x, y = zip(*points)
        return [min(x)/im.width, min(y)/im.height, max(x)/im.width, max(y)/im.height]
    a, b = zip(*pairs)
    first, second = box(a), box(b)
    if (first[2]-first[0]) * (first[3]-first[1]) < .003:
        return []
    return [finding("copy_move", MANIPULATION, "Repeated image features align under a common shift.",
                    location(doc, page, first), related=[location(doc, page, second)],
                    method="ORB descriptors clustered by translation",
                    limits="Weak signal. Repeated template art can look similar. Rotated and low-texture patches may be missed.",
                    confidence=.52, values={"aligned_pairs": len(pairs)})]
