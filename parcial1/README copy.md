# Primer Parcial · Lenguaje de Programación I

| Tramo | Qué | Dónde | Tiempo |
| --- | --- | --- | --- |
| 1 | Código: E1 y E2 ([enunciado](parcial1/README.md)) | su repo `<nombre-apellido>` | ~45 min, hasta la **hora límite del push** |
| 2 | Teoría | cuestionario de **Moodle** | ~25 min |

- **El cuestionario de Moodle se abre cuando termina el tiempo de código**, no antes. Varias preguntas del cuestionario son sobre el código de E1 y E2 que usted entregó en su repositorio. Téngalo abierto durante el tramo 2. Después de la hora límite ya no se pueden cambiar: lo que se empuje más tarde no cuenta.
- **Internet** solo para Moodle, GitHub y la documentación de Python ([docs.python.org](https://docs.python.org/3.14/)). Usar IA, chats u otros sitios anula el parcial.

## Cómo se entrega el código (GitHub)

Se trabaja en su repositorio del curso, `<nombre-apellido>`, dentro de una carpeta `parcial1/`:

```
<nombre-apellido>/
└── parcial1/
    ├── README.md          (el enunciado)
    ├── e1_sensores.py     (E1)
    └── e2_inventario.py   (E2)
```

### 1. Copiar el enunciado (minuto 0)

En la terminal (Git Bash en Windows), dentro de la carpeta de su repositorio:

```bash
git pull
git clone https://github.com/programming-language-i/parcial-01.git ../parcial1-enunciado
cp -r ../parcial1-enunciado/parcial1 parcial1
```

Sin `git clone`: en esta página use **Code → Download ZIP**, descomprima y copie la carpeta `parcial1/` a su repositorio.

### 2. Primer commit y push (antes de empezar a resolver)

```bash
git add parcial1
git commit -m "parcial1: inicio"
git push
```

Abra su repositorio en github.com y confirme que aparece `parcial1/`. **Si el push falla, avísele al docente en ese momento**, no al final.

### 3. Commits durante el tramo 1 (mínimo 2)

Haga commit y push al terminar cada ejercicio:

```bash
git add parcial1
git commit -m "parcial1: E1 resuelto"
git push
# ... y lo mismo con E2:
git add parcial1
git commit -m "parcial1: E2 resuelto"
git push
```

### 4. Hora límite del código

- Haga el último `git push` **antes de la hora límite que anuncia el docente**. Después se abre Moodle.
- Se califica el **último push anterior a la hora límite**. La hora la registra GitHub, no su computador.
- Revise en github.com que sus archivos estén ahí.

### Si el push no funciona

Comprima la carpeta `parcial1/` en `<nombre-apellido>.zip`, envie un correo con la solucion antes de la hora límite y avísele al docente.
