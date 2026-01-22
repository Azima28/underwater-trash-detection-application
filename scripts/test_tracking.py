#!/usr/bin/env python3
"""
Simple test script untuk verify centroid tracking logic
"""
import numpy as np

def get_centroid(box):
    """Get centroid dari bounding box [x1, y1, x2, y2]"""
    x1, y1, x2, y2 = box[:4]
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return np.array([cx, cy])

def distance(p1, p2):
    """Euclidean distance antara 2 points"""
    return np.linalg.norm(p1 - p2)

def match_detections(prev_boxes, curr_boxes, max_distance=50):
    """
    Match current detections dengan previous frame detections.
    Return: list of (current_idx, prev_idx) untuk matched detections, dan list of new indices
    """
    if len(prev_boxes) == 0:
        return [], list(range(len(curr_boxes)))
    
    if len(curr_boxes) == 0:
        return [], []
    
    # Compute centroids
    prev_centroids = [get_centroid(box) for box in prev_boxes]
    curr_centroids = [get_centroid(box) for box in curr_boxes]
    
    # Match based on distance
    matched = []
    used_prev = set()
    used_curr = set()
    
    for curr_idx, curr_cent in enumerate(curr_centroids):
        best_dist = max_distance
        best_prev_idx = -1
        
        for prev_idx, prev_cent in enumerate(prev_centroids):
            if prev_idx in used_prev:
                continue
            
            d = distance(curr_cent, prev_cent)
            if d < best_dist:
                best_dist = d
                best_prev_idx = prev_idx
        
        if best_prev_idx >= 0:
            matched.append((curr_idx, best_prev_idx))
            used_prev.add(best_prev_idx)
            used_curr.add(curr_idx)
    
    new_indices = [i for i in range(len(curr_boxes)) if i not in used_curr]
    return matched, new_indices

# Test case 1: Same object moves slightly
print("Test 1: Object moves from frame 1 to frame 2")
frame1_boxes = [np.array([100, 100, 200, 200, 0.9])]  # trash at (150, 150)
frame2_boxes = [np.array([105, 105, 205, 205, 0.9])]  # trash at (155, 155) - moved 7 pixels
matched, new = match_detections(frame1_boxes, frame2_boxes, max_distance=50)
print(f"  Matched: {matched}, New: {new}")
print(f"  Expected: 1 matched (same object), 0 new - Status: {'✓ PASS' if len(matched)==1 and len(new)==0 else '✗ FAIL'}\n")

# Test case 2: Object disappears (no new object)
print("Test 2: Object disappears from frame 1")
frame1_boxes = [np.array([100, 100, 200, 200, 0.9])]
frame2_boxes = []
matched, new = match_detections(frame1_boxes, frame2_boxes, max_distance=50)
print(f"  Matched: {matched}, New: {new}")
print(f"  Expected: 0 matched, 0 new - Status: {'✓ PASS' if len(matched)==0 and len(new)==0 else '✗ FAIL'}\n")

# Test case 3: New object appears
print("Test 3: New object appears in frame 2")
frame1_boxes = []
frame2_boxes = [np.array([300, 300, 400, 400, 0.9])]
matched, new = match_detections(frame1_boxes, frame2_boxes, max_distance=50)
print(f"  Matched: {matched}, New: {new}")
print(f"  Expected: 0 matched, 1 new - Status: {'✓ PASS' if len(matched)==0 and len(new)==[0] else '✗ FAIL'}\n")

# Test case 4: Multiple objects with mix of tracking and new
print("Test 4: 2 objects in frame 1, 2 in frame 2 (1 tracked + 1 new)")
frame1_boxes = [
    np.array([100, 100, 200, 200, 0.9]),  # obj A at (150, 150)
    np.array([300, 300, 400, 400, 0.9])   # obj B at (350, 350) - stays
]
frame2_boxes = [
    np.array([105, 105, 205, 205, 0.9]),  # obj A at (155, 155) - moved 7 pixels
    np.array([500, 500, 600, 600, 0.9])   # new object at (550, 550)
]
matched, new = match_detections(frame1_boxes, frame2_boxes, max_distance=50)
print(f"  Matched: {matched}, New: {new}")
print(f"  Expected: 1 matched, 1 new - Status: {'✓ PASS' if len(matched)==1 and len(new)==1 else '✗ FAIL'}\n")

# Test case 5: Objects too far apart (should be new objects)
print("Test 5: Object moves too far (100 pixels, threshold 50)")
frame1_boxes = [np.array([0, 0, 100, 100, 0.9])]      # at (50, 50)
frame2_boxes = [np.array([150, 150, 250, 250, 0.9])]  # at (200, 200) - 212 pixels away
matched, new = match_detections(frame1_boxes, frame2_boxes, max_distance=50)
print(f"  Matched: {matched}, New: {new}")
print(f"  Expected: 0 matched, 1 new (different object) - Status: {'✓ PASS' if len(matched)==0 and len(new)==[0] else '✗ FAIL'}\n")

print("=" * 60)
print("Tracking logic test complete!")
print("If all tests PASS, the centroid tracking should work correctly.")
