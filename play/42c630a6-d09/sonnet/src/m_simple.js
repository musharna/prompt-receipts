const F = (title, text, p, q, side, o = {}) => Object.assign({ type: 'fold', title, text, p, q, side }, o);
const UNDO = (title, text) => ({ type: 'undo', title, text });
const top = z => (i => i.cz > z);

exports.waterbomb = {
  name: 'Waterbomb', rot: 0, top: '#2f80ed', back: '#fff8e8',
  steps: [
    F('Fold in half', 'Fold the top edge down to the bottom edge to make a rectangle.', [-.5, 0], [.5, 0], 1),
    F('Pinch the middle', 'Fold the left side over to the right...', [0, -.5], [0, .5], 1),
    UNDO('Unfold', '...and open it again. You now have a crease down the middle.'),
    F('Fold the left corner', 'Fold the top left corner down along a slanted crease so the top edge lies on the middle crease.', [0, 0], [-.5, -.5], -1),
    F('Fold the right corner', 'Do the same on the right. You have a triangle, like a little hat.', [0, 0], [.5, -.5], 1),
    F('Left corner to the top', 'Fold the left point of the triangle up to the top point. All layers together.', [-.25, -.25], [0, -.5], -1),
    F('Right corner to the top', 'Fold the right point up to the top point too. You have a square, standing on its corner.', [.25, -.25], [0, -.5], 1),
    F('Fold the front tip down', 'On the front layer only, fold the top tip down to the middle. This will be tucked into the pocket.', [-.3, -.125], [.3, -.125], 1, { sel: (i, c) => i.cz > c.zmax - .002 }),
    { type: 'rotate', title: 'Turn over', text: 'Flip the model over, left to right.', p: [0, -.25], q: [0, 0] },
    F('Fold the back tip down', 'Fold the other top tip down the same way.', [-.3, -.125], [.3, -.125], 1, { sel: (i, c) => i.cz > c.zmax - .002 })
  ]
};

exports.frog = {
  name: 'Jumping Frog', rot: 0, top: '#3fae5a', back: '#f4ffe9',
  steps: [
    F('Fold the bottom up', 'Fold the bottom edge up a little. This is the first half of the spring.', [-.5, -.3], [.5, -.3], -1),
    F('Fold it back down', 'Fold the new bottom edge back down halfway. The zig-zag (a Z) is the frog\u2019s spring.', [-.5, -.2], [.5, -.2], 1, { sel: (i, c) => i.cz > c.zmax - .002 }),
    F('Pinch the middle', 'Fold the paper in half, left over right...', [0, -.5], [0, .5], 1),
    UNDO('Unfold', '...and open it. This crease is the frog\u2019s backbone.'),
    F('Fold the left roof', 'Fold the top left corner to the middle of the paper.', [-.5, 0], [0, .5], 1),
    F('Fold the right roof', 'Fold the top right corner to the middle too. It looks like a house.', [.5, 0], [0, .5], -1),
    F('Fold the left side in', 'Fold the left side in towards the middle.', [-.3, -.5], [-.3, .5], 1),
    F('Fold the right side in', 'Fold the right side in as well. Now it\u2019s a rocket with a Z-shaped tail!', [.3, .5], [.3, -.5], 1),
    F('Round the head', 'Fold the pointy top of the head down to make a rounded frog face.', [-.5, .42], [.5, .42], 1),
    F('Left hind leg', 'Fold the bottom left corner up and in to make a hind leg.', [-.3, -.12], [-.12, -.3], -1),
    F('Right hind leg', 'Fold the bottom right corner up and in too. Your frog is ready!', [.12, -.3], [.3, -.12], -1),
    { type: 'hop', title: 'Jump!', text: 'Press down on the back with a finger and slide it off. The spring flicks the frog into the air!' }
  ]
};

exports.sailboat = {
  name: 'Sailboat', rot: 45, top: '#e0533d', back: '#ffffff',
  steps: [
    F('Mark the waterline', 'Fold the top corner down to the bottom corner.', [-.5, 0], [.5, 0], 1),
    UNDO('Unfold', 'Open it up again. The crease is the waterline.'),
    F('Make the hull', 'Fold the bottom corner up to the middle. This is the boat’s hull.', [-.5, -.354], [.5, -.354], -1),
    F('Shape the left sail', 'Fold the left side of the sail back behind, from the top point down to the waterline.', [0, .707], [-.35, 0], -1, { dir: 'm', sel: i => i.cy > 0 }),
    F('Shape the right sail', 'Fold the right side back too. Your sailboat is ready to sail!', [0, .707], [.35, 0], 1, { dir: 'm', sel: i => i.cy > 0 })
  ]
};
