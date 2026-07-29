export type PositionedMapItem = {
  id: string;
  map_x: string | null;
  map_y: string | null;
};

function coordinate(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function orderBoothVisitGroups<T extends PositionedMapItem>(
  groups: T[][],
  entrance = { x: 50, y: 100 },
) {
  const remaining = [...groups];
  const ordered: T[][] = [];
  let current = entrance;
  while (remaining.length) {
    let nearestIndex = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;
    remaining.forEach((group, index) => {
      const booth = group[0];
      const x = coordinate(booth.map_x, 50);
      const y = coordinate(booth.map_y, 50);
      const distance = Math.hypot(x - current.x, y - current.y);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    });
    const [next] = remaining.splice(nearestIndex, 1);
    ordered.push(next);
    current = {
      x: coordinate(next[0].map_x, 50),
      y: coordinate(next[0].map_y, 50),
    };
  }
  return ordered;
}
