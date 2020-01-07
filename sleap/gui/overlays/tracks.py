"""
Module that handles track-related overlays (including track color).
"""

from sleap.instance import Track
from sleap.io.dataset import Labels
from sleap.io.video import Video

import attr
import itertools

from typing import List

from PySide2 import QtCore, QtGui


@attr.s(auto_attribs=True)
class TrackTrailOverlay:
    """Class to show track trails as overlay on video frame.

    Initialize this object with both its data source and its visual output
    scene, and it handles both extracting the relevant data for a given
    frame and plotting it in the output.

    Attributes:
        labels: The :class:`Labels` dataset from which to get overlay data.
        player: The video player in which to show overlay.
        trail_length: The maximum number of frames to include in trail.

    Usage:
        After class is instantiated, call :meth:`add_to_scene(frame_idx)`
        to plot the trails in scene.
    """

    labels: Labels = None
    player: "QtVideoPlayer" = None
    trail_length: int = 10
    show: bool = False

    def get_track_trails(self, frame_selection, track: Track):
        """Get data needed to draw track trail.

        Args:
            frame_selection: an interable with the :class:`LabeledFrame`
                objects to include in trail.
            track: the :class:`Track` for which to get trail

        Returns:
            list of lists of (x, y) tuples
                i.e., for every node in instance, we get a list of positions
        """

        all_trails = [[] for _ in range(len(self.labels.nodes))]

        for frame in frame_selection:
            frame_idx = frame.frame_idx

            inst_on_track = [instance for instance in frame if instance.track == track]
            if inst_on_track:
                # just use the first instance from this track in this frame
                inst = inst_on_track[0]
                # loop through all nodes
                for node_i, node in enumerate(self.labels.nodes):

                    if node in inst.nodes and inst[node].visible:
                        point = (inst[node].x, inst[node].y)
                    elif len(all_trails[node_i]):
                        point = all_trails[node_i][-1]
                    else:
                        point = None

                    if point is not None:
                        all_trails[node_i].append(point)

        return all_trails

    def get_frame_selection(self, video: Video, frame_idx: int):
        """
        Return `LabeledFrame` objects to include in trail for specified frame.
        """

        frame_selection = self.labels.find(video, range(0, frame_idx + 1))
        frame_selection.sort(key=lambda x: x.frame_idx)

        return frame_selection[-self.trail_length :]

    def get_tracks_in_frame(
        self, video: Video, frame_idx: int, include_trails: bool = False
    ) -> List[Track]:
        """
        Returns list of tracks that have instance in specified frame.

        Args:
            video: Video for which we want tracks.
            frame_idx: Frame index for which we want tracks.
            include_trails: Whether to include tracks which aren't in current
                frame but would be included in trail (i.e., previous frames
                within trail_length).
        Returns:
            List of tracks.
        """

        if include_trails:
            lfs = self.get_frame_selection(video, frame_idx)
        else:
            lfs = self.labels.find(video, frame_idx)

        tracks_in_frame = [inst.track for lf in lfs for inst in lf]

        return tracks_in_frame

    def add_to_scene(self, video: Video, frame_idx: int):
        """Plot the trail on a given frame.

        Args:
            video: current video
            frame_idx: index of the frame to which the trail is attached
        """
        if not self.show:
            return

        frame_selection = self.get_frame_selection(video, frame_idx)
        tracks_in_frame = self.get_tracks_in_frame(
            video, frame_idx, include_trails=True
        )

        for track in tracks_in_frame:

            trails = self.get_track_trails(frame_selection, track)

            color = QtGui.QColor(*self.player.color_manager.get_track_color(track))
            pen = QtGui.QPen()
            pen.setCosmetic(True)

            for trail in trails:
                half = len(trail) // 2

                color.setAlphaF(1)
                pen.setColor(color)
                polygon = self.map_to_qt_polygon(trail[:half])
                self.player.scene.addPolygon(polygon, pen)

                color.setAlphaF(0.5)
                pen.setColor(color)
                polygon = self.map_to_qt_polygon(trail[half:])
                self.player.scene.addPolygon(polygon, pen)

    @staticmethod
    def map_to_qt_polygon(point_list):
        """Converts a list of (x, y)-tuples to a `QPolygonF`."""
        return QtGui.QPolygonF(list(itertools.starmap(QtCore.QPointF, point_list)))


@attr.s(auto_attribs=True)
class TrackListOverlay:
    """
    Class to show track number and names in overlay.
    """

    labels: Labels = None
    player: "QtVideoPlayer" = None
    text_box = None

    def add_to_scene(self, video: Video, frame_idx: int):
        """Adds track list as overlay on video."""
        from sleap.gui.video import QtTextWithBackground

        html = ""
        num_to_show = min(9, len(self.labels.tracks))

        for i, track in enumerate(self.labels.tracks[:num_to_show]):
            idx = i + 1

            if html:
                html += "<br />"
            color = self.player.color_manager.get_track_color(track)
            html_color = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
            track_text = f"<b>{track.name}</b>"
            if str(idx) != track.name:
                track_text += f" ({idx})"
            html += f"<span style='color:{html_color}'>{track_text}</span>"

        text_box = QtTextWithBackground()
        text_box.setDefaultTextColor(QtGui.QColor("white"))
        text_box.setHtml(html)
        text_box.setOpacity(0.7)

        self.text_box = text_box
        self.visible = False

        self.player.scene.addItem(self.text_box)

    @property
    def visible(self):
        """Gets or set whether overlay is visible."""
        if self.text_box is None:
            return False
        return self.text_box.isVisible()

    @visible.setter
    def visible(self, val):
        if self.text_box is None:
            return
        if val:
            pos = self.player.view.mapToScene(10, 10)
            if pos.x() > 0:
                self.text_box.setPos(pos)
            else:
                self.text_box.setPos(10, 10)
        self.text_box.setVisible(val)