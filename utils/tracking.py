import numpy as np
from collections import OrderedDict

class CentroidTracker:
    def __init__(self, max_disappeared=50, max_distance=50):
        # Initialize the next unique object ID along with two ordered
        # dictionaries used to keep track of mapping a given object
        # ID to its centroid and number of consecutive frames it has
        # been marked as "disappeared", respectively
        self.next_object_id = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.class_names = OrderedDict() # Store class name for each object ID

        # Store the number of maximum consecutive frames a given
        # object is allowed to be marked as "disappeared" until we
        # need to deregister the object from tracking
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid, class_name):
        # When registering an object we use the next available object
        # ID to store the centroid
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.class_names[self.next_object_id] = class_name
        self.next_object_id += 1

    def deregister(self, object_id):
        # To deregister an object ID we delete the object ID from
        # both of our respective dictionaries
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.class_names[object_id]

    def update(self, rects, class_names_list):
        # Check to see if the list of input bounding box rectangles
        # is empty
        if len(rects) == 0:
            # Loop over any existing tracked object IDs and mark them
            # as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1

                # If we have reached a maximum number of consecutive
                # frames where a given object has been marked as
                # missing, deregister it
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Return early as there are no centroids or tracking info
            # to update
            return self.objects, self.class_names

        # Initialize an array of input centroids for the current frame
        input_centroids = np.zeros((len(rects), 2), dtype="int")

        # Loop over the bounding box rectangles
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            # Use the bounding box coordinates to derive the centroid
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            input_centroids[i] = (cX, cY)

        # If we are currently not tracking any objects, take the input
        # centroids and register each of them
        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(input_centroids[i], class_names_list[i])

        # Otherwise, are are currently tracking objects so we need to
        # match the input centroids to existing object centroids
        else:
            # Grab the set of object IDs and corresponding centroids
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Compute the distance between each pair of object
            # centroids and input centroids, respectively -- our
            # goal will be to match an input centroid to an existing
            # object centroid
            if len(object_ids) > 0 and len(input_centroids) > 0:
                # Manual Euclidean distance calculation to avoid dependency issues if needed, 
                # but numpy linalg norm is standard.
                # Distance matrix: rows = existing objects, cols = input objects
                D = np.zeros((len(object_ids), len(input_centroids)))
                for i in range(len(object_ids)):
                    for j in range(len(input_centroids)):
                        D[i, j] = np.linalg.norm(np.array(object_centroids[i]) - input_centroids[j])
                
                # In order to perform this matching we must (1) find the
                # smallest value in each row and then (2) sort the row
                # indexes based on their minimum values so that the row
                # with the smallest value is at the *front* of the index
                # list
                rows = D.min(axis=1).argsort()

                # Next, we perform a similar process on the columns by
                # finding the smallest value in each column and then
                # sorting using the previously computed row index list
                cols = D.argmin(axis=1)[rows]

                # In order to determine if we need to update, register,
                # or deregister an object we need to keep track of which
                # of the rows and column indexes we have already examined
                used_rows = set()
                used_cols = set()

                # Loop over the combination of the (row, column) index
                # tuples
                for (row, col) in zip(rows, cols):
                    # If we have already examined either the row or
                    # column value before, ignore it
                    if row in used_rows or col in used_cols:
                        continue

                    # If the distance between centroids is greater than
                    # the maximum distance, do not associate the two
                    # centroids to the same object
                    if D[row, col] > self.max_distance:
                        continue

                    # Otherwise, grab the object ID for the current row,
                    # set its new centroid, and reset the disappeared
                    # counter
                    object_id = object_ids[row]
                    self.objects[object_id] = input_centroids[col]
                    self.disappeared[object_id] = 0
                    self.class_names[object_id] = class_names_list[col] # Update class name (optional, usually stays same)

                    # Indicate that we have examined each of the row and
                    # column indexes, respectively
                    used_rows.add(row)
                    used_cols.add(col)

                # Compute both the row and column index we have NOT yet
                # examined
                unused_rows = set(range(0, D.shape[0])).difference(used_rows)
                unused_cols = set(range(0, D.shape[1])).difference(used_cols)

                # In the event that the number of object centroids is
                # equal or greater than the number of input centroids
                # we need to check and see if some of these objects have
                # potentially disappeared
                if D.shape[0] >= D.shape[1]:
                    # Loop over the unused row indexes
                    for row in unused_rows:
                        object_id = object_ids[row]
                        self.disappeared[object_id] += 1

                        if self.disappeared[object_id] > self.max_disappeared:
                            self.deregister(object_id)

                # Otherwise, if the number of input centroids is greater
                # than the number of existing object centroids we need to
                # register each new input centroid as a trackable object
                else:
                    for col in unused_cols:
                        self.register(input_centroids[col], class_names_list[col])
                        
            # If no existing objects (failsafe, though handled by len(object_ids) check)
            else:
                 for i in range(0, len(input_centroids)):
                    self.register(input_centroids[i], class_names_list[i])

        # Return the set of trackable objects
        # We also need to count total unique objects seen across the session?
        # The class maintains current objects. For a cumulative count, 
        # the caller needs to track 'next_object_id'.
        return self.objects, self.class_names
