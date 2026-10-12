import { describe, it, expect } from 'vitest';
import { whatsappUrl, fillTemplate } from '../src/lib/whatsapp.js';

describe('whatsappUrl', () => {
  it('arma el link con el número en dígitos y el mensaje codificado', () => {
    expect(whatsappUrl('+54 9 11 5555-0000', 'Hola, ¿qué tal?')).toBe(
      'https://wa.me/5491155550000?text=Hola%2C%20%C2%BFqu%C3%A9%20tal%3F',
    );
  });

  it('sin número configurado igual abre WhatsApp con el mensaje', () => {
    expect(whatsappUrl('', 'Hola')).toBe('https://wa.me/?text=Hola');
  });

  it('sin mensaje no agrega el parámetro text', () => {
    expect(whatsappUrl('5491155550000', '')).toBe('https://wa.me/5491155550000');
  });
});

describe('fillTemplate', () => {
  it('reemplaza las variables entre llaves', () => {
    expect(fillTemplate('Clase {n} de {curso}', { n: 4, curso: 'CRT' })).toBe('Clase 4 de CRT');
  });

  it('deja intacta una variable que no recibió valor', () => {
    expect(fillTemplate('Hola {nombre}', {})).toBe('Hola {nombre}');
  });
});
