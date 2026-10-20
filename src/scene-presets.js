export const SCENE_THEMES = [
  { id: 'forest', name: 'Floresta', colors: ['#182b23', '#507b50'] },
  { id: 'ocean', name: 'Oceano', colors: ['#1b2635', '#4c7294'] },
  { id: 'sunset', name: 'Crepúsculo', colors: ['#30263b', '#9b648b'] },
  { id: 'amber', name: 'Âmbar', colors: ['#302c21', '#a58a55'] },
  { id: 'mint', name: 'Menta', colors: ['#172e30', '#4c8788'] },
  { id: 'slate', name: 'Ardósia', colors: ['#292e31', '#597282'] },
];
export const SCENE_TRANSITIONS = [
  { id: 'fade', name: 'Suave (fade)' },
  { id: 'cut', name: 'Corte direto' },
];
export function defaultSceneTheme(index) {
  return SCENE_THEMES[index % SCENE_THEMES.length].id;
}
export function sceneTheme(id, index = 0) {
  return SCENE_THEMES.find(t => t.id === id) || SCENE_THEMES[index % SCENE_THEMES.length];
}
export function safeSceneTransition(value) {
  return value === 'cut' ? 'cut' : 'fade';
}
