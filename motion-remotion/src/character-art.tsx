import React, { useCallback, useLayoutEffect, useRef } from 'react';
import { Img, staticFile } from 'remotion';

type Eye = [number, number, number, number];
type Face = {
  box: [number, number, number, number];
  eyes: Eye[];
  arm?: [number, number, number, number];
};
export type Performance = {
  width: number;
  height: number;
  seed: number;
  faces: Face[];
  motion: 'eyes' | 'portrait' | 'cutout';
};

const ease = (v: number) => {
  const p = Math.max(0, Math.min(1, v));
  return p * p * (3 - 2 * p);
};

function paintEye(ctx: CanvasRenderingContext2D, eye: Eye, gaze: number, blink: number) {
  if (!blink && !gaze) return;
  const [cx, cy, irisRadius, halfHeight] = eye;
  const rx = irisRadius * 1.65,
    ry = halfHeight * 1.3,
    extent = 2.6;
  const left = Math.max(0, Math.floor(cx - rx) - 1),
    top = Math.max(0, Math.floor(cy - ry * extent) - 1);
  const width = Math.min(ctx.canvas.width, Math.ceil(cx + rx) + 2) - left;
  const height = Math.min(ctx.canvas.height, Math.ceil(cy + ry * extent) + 2) - top;
  const src = ctx.getImageData(left, top, width, height);
  const dst = new ImageData(new Uint8ClampedArray(src.data), width, height);
  for (let i = 0; i < width; i++) {
    const nx = (left + i - cx) / rx;
    if (Math.abs(nx) >= 1) continue;
    // Squeeze the original aperture along its arc. The ink of both lashes
    // travels with the lid and the adjacent skin supplies its own texture.
    const h = ry * Math.sqrt(1 - nx * nx);
    const closure = blink * ease((1 - Math.abs(nx)) / 0.34);
    const upper = -1 + 1.52 * closure,
      lower = 1 - 0.34 * closure;
    for (let j = 0; j < height; j++) {
      const ny = (top + j - cy) / h;
      if (Math.abs(ny) >= extent) continue;
      let fromY: number;
      if (ny < upper) fromY = -extent + ((ny + extent) * (extent - 1)) / (upper + extent);
      else if (ny > lower) fromY = 1 + ((ny - lower) * (extent - 1)) / (extent - lower);
      else fromY = -1 + (2 * (ny - upper)) / (lower - upper);
      const inside = ease((1 - Math.abs(fromY)) / 0.42) * ease((1 - Math.abs(nx)) / 0.34);
      const sx = Math.max(0, Math.min(width - 1.001, i - gaze * irisRadius * 0.16 * inside));
      const sy = Math.max(0, Math.min(height - 1.001, cy + fromY * h - top));
      const ix = Math.floor(sx),
        iy = Math.floor(sy),
        fx = sx - ix,
        fy = sy - iy;
      const a = 4 * (iy * width + ix),
        b = a + 4 * width,
        out = 4 * (j * width + i);
      for (let c = 0; c < 3; c++) {
        dst.data[out + c] =
          (1 - fy) * ((1 - fx) * src.data[a + c] + fx * src.data[a + 4 + c]) +
          fy * ((1 - fx) * src.data[b + c] + fx * src.data[b + 4 + c]);
      }
    }
  }
  ctx.putImageData(dst, left, top);
}

function movePortrait(
  ctx: CanvasRenderingContext2D,
  face: Face,
  isolated: boolean,
  turn: number,
  nod: number,
  breath: number,
) {
  if (!turn && !nod && !breath) return;
  const [x, y, w, h] = face.box;
  const cx = x + w * 0.5,
    pivot = y + h * 1.05;
  // A cutout can move from the neck through the crown. For a flat picture
  // taper the movement inside the facial oval to protect the surroundings.
  const rx = w * (isolated ? 1.3 : 0.48),
    ry = h * (isolated ? 1.28 : 0.49);
  const cy = y + h * (isolated ? 0.25 : 0.53);
  const chestY = y + 1.68 * h,
    chestRx = w * 1.22,
    chestRy = h * 0.7;
  const arm = isolated ? face.arm : undefined;
  const [elbowX, elbowY, handX, handY] = arm ?? [cx, cy, cx, cy];
  const armX = handX - elbowX,
    armY = handY - elbowY,
    length2 = armX ** 2 + armY ** 2;
  const tipX = handX + 0.48 * armX,
    tipY = handY + 0.48 * armY;
  const armRadius = arm ? 0.85 * w : 0;
  const left = Math.max(0, Math.floor(Math.min(cx - rx, elbowX - armRadius, tipX - armRadius)) - 1);
  const top = Math.max(0, Math.floor(Math.min(cy - ry, elbowY - armRadius, tipY - armRadius)) - 1);
  const right = Math.max(cx + rx, elbowX + armRadius, tipX + armRadius);
  const bottom = Math.max(
    cy + ry,
    isolated ? chestY + chestRy : cy,
    elbowY + armRadius,
    tipY + armRadius,
  );
  const width = Math.min(ctx.canvas.width, Math.ceil(right) + 1) - left;
  const height = Math.min(ctx.canvas.height, Math.ceil(bottom) + 1) - top;
  if (width < 3 || height < 3) return;
  const src = ctx.getImageData(left, top, width, height);
  const dst = new ImageData(new Uint8ClampedArray(src.data), width, height);
  const angle = turn * (isolated ? 0.024 : 0.009);
  const dy = nod * h * (isolated ? 0.014 : 0.008);
  for (let j = 1; j < height - 1; j++) {
    const py = top + j,
      ny = (py - cy) / ry;
    for (let i = 1; i < width - 1; i++) {
      const px = left + i,
        nx = (px - cx) / rx;
      const r = nx * nx + ny * ny;
      const chest = isolated
        ? ease(1 - ((px - cx) / chestRx) ** 2 - ((py - chestY) / chestRy) ** 2)
        : 0;
      let armAngle = 0;
      if (arm && length2 > 0) {
        const along = ((px - elbowX) * armX + (py - elbowY) * armY) / length2;
        const lateral = ((px - elbowX) * armY - (py - elbowY) * armX) ** 2 / length2;
        armAngle =
          0.036 *
          nod *
          ease(along / 0.45) *
          ease((1.5 - along) / 0.3) *
          ease((1 - lateral / armRadius ** 2) / 0.75);
      }
      if (r >= 1 && !chest && !armAngle) continue;
      const weight = ease((1 - r) / 0.56);
      const sx = Math.max(
        0,
        Math.min(width - 1.001, i - weight * (pivot - py) * angle + armAngle * (py - elbowY)),
      );
      const sy = Math.max(
        0,
        Math.min(
          height - 1.001,
          j -
            weight * ((px - cx) * angle + dy) +
            chest * breath * h * 0.014 -
            armAngle * (px - elbowX),
        ),
      );
      const ix = Math.floor(sx),
        iy = Math.floor(sy),
        fx = sx - ix,
        fy = sy - iy;
      const a = 4 * (iy * width + ix),
        b = a + 4 * width,
        out = 4 * (j * width + i);
      // Interpolate premultiplied color at the transparent hair silhouette.
      const k0 = (1 - fx) * (1 - fy) * src.data[a + 3],
        k1 = fx * (1 - fy) * src.data[a + 7];
      const k2 = (1 - fx) * fy * src.data[b + 3],
        k3 = fx * fy * src.data[b + 7];
      const alpha = k0 + k1 + k2 + k3;
      dst.data[out + 3] = alpha;
      if (alpha > 0) {
        for (let c = 0; c < 3; c++)
          dst.data[out + c] =
            (k0 * src.data[a + c] +
              k1 * src.data[a + 4 + c] +
              k2 * src.data[b + c] +
              k3 * src.data[b + 4 + c]) /
            alpha;
      }
    }
  }
  ctx.putImageData(dst, left, top);
}

export const CharacterArt: React.FC<{
  src: string;
  plan?: Performance;
  style: React.CSSProperties;
  second: number;
}> = ({ src, plan, style, second }) => {
  const photo = useRef<HTMLImageElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const paint = useCallback(() => {
    const img = photo.current,
      surface = canvas.current;
    if (!plan || !img?.complete || !img.naturalWidth || !surface) return;
    const ctx = surface.getContext('2d', { willReadFrequently: true });
    if (!ctx) return;
    ctx.clearRect(0, 0, surface.width, surface.height);
    ctx.drawImage(img, 0, 0, plan.width, plan.height);
    plan.faces.forEach((face, index) => {
      const salt = (((plan.seed % 997) + index * 421) % 997) / 997;
      const t = Math.max(0, second) % (4.2 + 1.6 * salt);
      const event = t - 0.24 - 0.56 * salt;
      const direction = Math.floor(salt * 16) % 2 ? 1 : -1;
      const turn = ease((event - 0.38) / 0.66) * (1 - ease((event - 1.68) / 0.76));
      const gaze =
        direction *
        ease((event - 0.16) / 0.16) *
        (1 - ease((event - 1.53) / 0.22)) *
        (1 - 0.55 * turn);
      const blink = ease(event / 0.1) * (1 - ease((event - 0.12) / 0.17));
      const nod = ease((event - 0.6) / 0.85) * (1 - ease((event - 2.04) / 0.72));
      for (const eye of face.eyes) paintEye(ctx, eye, gaze, blink);
      const breath = Math.sin((Math.PI * t) / (4.2 + 1.6 * salt)) ** 2;
      if (plan.motion !== 'eyes')
        movePortrait(ctx, face, plan.motion === 'cutout', direction * turn, nod, breath);
    });
  }, [plan, second]);
  useLayoutEffect(paint, [paint, src]);
  if (!plan) return <Img src={staticFile(src)} style={style} />;
  return (
    <>
      <Img key={src} ref={photo} src={staticFile(src)} style={{ display: 'none' }} onLoad={paint} />
      <canvas ref={canvas} width={plan.width} height={plan.height} style={style} />
    </>
  );
};
