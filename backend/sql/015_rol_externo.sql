-- Rol EXTERNO: solicitantes externos al equipo DOVELA (clientes), con acceso muy limitado al
-- portal (crear solicitudes, ver/editar solo las propias mientras estén "En espera", adjuntar
-- archivos y comentar a nivel solicitud). El Scrum Master lo asigna igual que cualquier otro rol
-- desde la página "Usuarios" (esa página ya carga los roles dinámicamente vía GET /roles-scrum).

INSERT INTO roles_scrum (codigo, descripcion, orden_visualizacion) VALUES
    ('EXTERNO', 'Externo', 4);
