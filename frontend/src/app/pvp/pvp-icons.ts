// Utilidades centralizadas para rutas de iconos y labels

export function iconFaction(f:number){
  if(f === 1) return 'images/faction/2.png'; // Horda
  if(f === 2) return 'images/faction/1.png'; // Alianza
  return 'images/faction/neutral.png';
}
export function labelFaction(f:number){
  if(f === 1) return 'Horda';
  if(f === 2) return 'Alianza';
  return 'Neutral';
}

export function iconRaceGender(race:number, gender:number){
  return `images/race/${race}-${gender}.gif`;
}
export function labelRaceGender(race:number, gender:number){
  return `Raza ${race} - ${gender === 0 ? 'Hombre' : 'Mujer'}`;
}

export function iconClass(cls:number){
  return `images/class/${cls}.gif`;
}
export function labelClass(cls:number){
  const map:Record<number,string> = {1:'Warrior',2:'Paladin',3:'Hunter',4:'Rogue',5:'Priest',6:'DK',7:'Shaman',8:'Mage',9:'Warlock',10:'Monk',11:'Druid',12:'DH'};
  return map[cls] || 'Clase';
}
