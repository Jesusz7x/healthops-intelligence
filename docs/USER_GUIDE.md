# User guide / Manual de usuario

## English

1. Start the local server using [INSTALLATION.md](INSTALLATION.md), then sign in with one of the fictional demo accounts in the README.
2. **Dashboard** shows counts and a daily appointments chart. Counts reflect the synthetic seed dataset, not a real clinic.
3. **Patients** supports search, create, edit, active/inactive status, CSV import and CSV export. Imported emails must use `.invalid`; import rolls back if a row fails. Keep real patient information out of this demo.
4. **Appointments** lists time, patient, staff and status. Create an appointment using active sample patient/staff IDs. A staff member cannot be double-booked at the same normalized time. Scheduled records can transition once to completed/cancelled/no-show.
5. **Staff & roles** lets administrators create directory entries and change seeded demo account roles/active flags. It prevents removing the last active administrator.
6. **Inventory** supports item creation, positive receipt/negative issue, a movement ledger, and non-negative stock enforcement.
7. **Reports & trends** compares the last seven calendar days with the previous seven, flags exploratory MAD outliers, shows inventory thresholds, data-quality findings, and a constant 28-day-mean baseline for the next week.
8. **Audit log** and **Settings** are administrator-only. Use the language and theme controls in the top bar.

## Español

1. Inicia el servidor local según [INSTALLATION.md](INSTALLATION.md) e ingresa con una cuenta ficticia del README.
2. **Panel** muestra cantidades y una gráfica diaria de citas. Los datos corresponden a semillas sintéticas, no a una clínica real.
3. **Pacientes** permite buscar, crear, editar, cambiar entre activo/inactivo e importar/exportar CSV. Los correos de importación deben usar `.invalid`; si una fila falla, se revierte toda la importación. No uses información real de pacientes.
4. **Citas** muestra fecha, paciente, personal y estado. El sistema no permite agendar dos citas al mismo miembro del personal a la misma hora normalizada. Una cita programada puede pasar una vez a completada/cancelada/no asistió.
5. **Personal y roles** permite al administrador agregar personas ficticias al directorio y cambiar rol/estado de cuentas demo. No permite desactivar al último administrador activo.
6. **Inventario** permite crear artículos, registrar entradas/salidas y consultar el libro de movimientos. El saldo no puede ser negativo.
7. **Informes y tendencias** compara siete días con los siete anteriores, muestra alertas exploratorias MAD, existencias, calidad de datos y una proyección constante basada en el promedio de 28 días.
8. **Auditoría** y **Configuración** son solo para administradores. El selector superior cambia idioma y tema.

### Public demo mode

Remote binding is disabled unless read-only mode is enabled. In read-only mode the UI exposes viewer access only, even for the seeded administrator credential. The demo still contains only fictional records. Read the security guide before deploying.
