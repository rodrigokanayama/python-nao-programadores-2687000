# Backend REST autônomo para controle de presença

Este documento descreve uma API REST autônoma para controle de presenças com cadastro próprio de usuários, organização por turmas, check-in via QR Code e geração de relatórios exportáveis.

## Perfis e fluxo geral
- **Professor**: cria conta, confirma e-mail, cadastra disciplinas e turmas, compartilha código ou link de convite, abre sessões, exibe QR Code, acompanha presença e gera relatórios.
- **Aluno**: cria conta, informa identificador (RA, CPF etc.), entra em turmas com código, lê o QR Code em aula, acompanha histórico e envia justificativas.
- **Admin global**: gerencia usuários, parametrizações (atraso, senha, formatos de relatório), termos e ambiente de produção.

## Entidades principais
- **User**: id, nome, email, password_hash, role (STUDENT, TEACHER, ADMIN), identificador opcional, criado_em.
- **Course**: id, nome, código, descrição (opcional; pode ser fundido com turma se preferir simplicidade).
- **Class**: id, course_id, teacher_id, nome, código da turma, semestre, descrição.
- **Enrollment**: id, class_id, student_id, status (ACTIVE, INACTIVE).
- **ClassSession**: id, class_id, data, hora_inicio_planejada, hora_fim_planejada, hora_inicio_real, hora_fim_real, status (PLANNED, ONGOING, CLOSED), token_atual, token_expira_em.
- **AttendanceRecord**: id, class_session_id, student_id, timestamp_checkin, status (PRESENT, LATE, ABSENT, JUSTIFIED_ABSENCE), source (QR_CODE, MANUAL), device_id, latitude, longitude.
- **AttendanceJustification**: id, attendance_record_id, student_id, texto, arquivo_url, status (PENDING, APPROVED, REJECTED), reviewer_id, data_decisao, comentario_revisor.
- **AuditLog**: id, actor_id, entity_type, entity_id, acao, dados_antes, dados_depois, criado_em.

## Autenticação
Autenticação por e-mail/senha com JWT.

### Registro
`POST /auth/register`

Request:
```json
{
  "name": "Rodrigo Kanayama",
  "email": "rodrigo@example.com",
  "password": "senha_forte",
  "role": "TEACHER",
  "identifier": "RA12345"
}
```

Response 201:
```json
{
  "id": 1,
  "name": "Rodrigo Kanayama",
  "email": "rodrigo@example.com",
  "role": "TEACHER"
}
```

### Login
`POST /auth/login`

Request:
```json
{
  "email": "rodrigo@example.com",
  "password": "senha_forte"
}
```

Response 200:
```json
{
  "access_token": "jwt-token-aqui",
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "name": "Rodrigo Kanayama",
    "email": "rodrigo@example.com",
    "role": "TEACHER"
  }
}
```

Tokens são enviados em `Authorization: Bearer <token>`.

## Disciplinas e turmas
### Disciplinas (opcional)
`POST /courses` (professor/admin)

```json
{
  "name": "Direito Financeiro",
  "code": "DFIN-01",
  "description": "Disciplina de Direito Financeiro."
}
```

Outros endpoints: `GET /courses`, `GET /courses/{id}`, `PUT /courses/{id}`, `DELETE /courses/{id}`.

### Turmas
`POST /classes` (professor)

```json
{
  "course_id": 1,
  "name": "Direito Financeiro - Turma A - 2025.1",
  "code": "DFIN-A-2025-1",
  "semester": "2025-1",
  "description": "Turma noturna."
}
```

Response inclui `join_code` para alunos:
```json
{
  "id": 10,
  "course_id": 1,
  "name": "Direito Financeiro - Turma A - 2025.1",
  "code": "DFIN-A-2025-1",
  "semester": "2025-1",
  "join_code": "ABC123"
}
```

Listagem e detalhes: `GET /classes` (conforme papel) e `GET /classes/{id}`.

## Matrícula
### Entrada do aluno via código
`POST /classes/join` (STUDENT)

```json
{
  "join_code": "ABC123"
}
```

Response:
```json
{
  "class_id": 10,
  "status": "ENROLLED"
}
```

### Lista de alunos da turma
`GET /classes/{classId}/students` (TEACHER)

## Sessões de aula
### Criação manual
`POST /classes/{classId}/sessions` (TEACHER)

```json
{
  "date": "2025-03-10",
  "planned_start_time": "18:40",
  "planned_end_time": "20:20"
}
```

Response cria sessão PLANNED. Sessões também podem ser geradas automaticamente a partir de horários semanais.

### Início da aula e QR dinâmico
`POST /sessions/{sessionId}/start` (TEACHER)

Request opcional de geolocalização:
```json
{
  "use_geolocation": true,
  "location": {
    "latitude": -25.4284,
    "longitude": -49.2733,
    "radius_meters": 50
  }
}
```

Response inclui token atual e expiração para o QR:
```json
{
  "id": 100,
  "status": "ONGOING",
  "current_token": "token-assinado",
  "token_expires_at": "2025-03-10T18:50:00Z"
}
```

### Renovação do token
`POST /sessions/{sessionId}/refresh-token` (TEACHER) retorna novo token e expiração.

### Encerramento da sessão
`POST /sessions/{sessionId}/end` (TEACHER) altera status para CLOSED.

## Check-in por QR Code
`POST /attendance/checkin` (STUDENT)

```json
{
  "token": "token-assinado-lido-do-qr",
  "device_id": "ios-xyz-123",
  "location": {
    "latitude": -25.4285,
    "longitude": -49.2731
  }
}
```

O backend valida token, janela de tempo, estado da sessão, matrícula e regras de horário (presente/atraso).

Exemplo de sucesso:
```json
{
  "session_id": 100,
  "class_id": 10,
  "status": "PRESENT",
  "checked_at": "2025-03-10T18:45:12Z",
  "message": "Presença registrada com sucesso."
}
```

## Consulta e ajustes de presença
- `GET /sessions/{sessionId}/attendance` (TEACHER): lista presenças de uma sessão.
- `PUT /attendance/{attendanceId}` (TEACHER): ajuste manual de status; registrar no AuditLog.

## Justificativas
- `POST /attendance/{attendanceId}/justifications` (STUDENT): envia justificativa com texto e anexo.
- `GET /classes/{classId}/justifications?status=PENDING` (TEACHER): lista pendências.
- `POST /justifications/{justificationId}/review` (TEACHER): aprova/rejeita e converte para falta justificada quando aplicável.

## Relatórios
- `GET /classes/{classId}/report/attendance`: visão por turma com totais de presenças/atrasos/faltas/faltas justificadas e percentual; aceitar filtros de data e `format=csv` para exportação.
- `GET /students/{studentId}/attendance-summary`: resumo de frequência do aluno em todas as turmas (professor ou o próprio aluno).

## Regras sugeridas
- Janelas de tempo configuráveis: presente até 15 minutos, atraso até 30; depois, ausência com ajuste manual.
- Percentual mínimo (ex.: 75%) apenas como indicador interno.
- Justificativas obrigatórias no app para converter ausência em falta justificada, mantendo trilha de auditoria.

## Observações de implementação
- Frontend mobile único para alunos e professores; painel web pode cobrir todas as funções do professor e administração.
- Tokens de sessão devem ser curtos e renovados periodicamente para QR dinâmico, evitando reutilização.
- Geolocalização é opcional, mas ajuda a evitar check-ins remotos.
- Exportação CSV/Excel e geração de PDF facilitam envio a coordenações sem depender de sistemas externos.
