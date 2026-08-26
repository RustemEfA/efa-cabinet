-- ============================================================
-- Storage-бакет для загруженных файлов (регламенты, результаты).
-- Запускать ПОСЛЕ 0001_init.sql.
-- Файлы хранятся приватно (public = false), доступ — только по
-- временной подписанной ссылке через API, никогда напрямую по URL.
-- ============================================================

insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

-- Путь внутри бакета: <user_id>/<project_id>/<filename>
-- Политики ниже разрешают юзеру читать/писать только внутри СВОЕЙ папки
-- (первая часть пути = его auth.uid()).

create policy "documents bucket: read own folder"
on storage.objects for select
using (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "documents bucket: upload to own folder"
on storage.objects for insert
with check (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "documents bucket: delete own folder"
on storage.objects for delete
using (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);
