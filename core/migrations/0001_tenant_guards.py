from __future__ import annotations

from django.db import migrations

GLOBAL_TABLE_EXCLUSIONS = (
    "tenants_tenant",
    "tenants_tenantdomain",
    "subscriptions_subscriptionplan",
    "featureflags_featurecatalog",
)


def apply_postgres_tenant_guards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uniq_branch_id_tenant'
                ) THEN
                    ALTER TABLE public.restaurants_branch
                    ADD CONSTRAINT uniq_branch_id_tenant UNIQUE (id, tenant_id);
                END IF;
            END $$;
            """
        )

        cursor.execute(
            """
            DO $$
            DECLARE
                r RECORD;
                cname text;
            BEGIN
                FOR r IN
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = 'branch_id'
                      AND table_name <> 'restaurants_branch'
                LOOP
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = r.table_name
                          AND column_name = 'tenant_id'
                    ) THEN
                        cname := r.table_name || '_branch_tenant_fk';
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = cname
                        ) THEN
                            EXECUTE format(
                                'ALTER TABLE public.%I ADD CONSTRAINT %I FOREIGN KEY (branch_id, tenant_id) REFERENCES public.restaurants_branch (id, tenant_id) DEFERRABLE INITIALLY DEFERRED',
                                r.table_name,
                                cname
                            );
                        END IF;
                    END IF;
                END LOOP;
            END $$;
            """
        )

        cursor.execute(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = 'tenant_id'
                LOOP
                    IF r.table_name NOT IN ('tenants_tenant', 'tenants_tenantdomain', 'subscriptions_subscriptionplan', 'featureflags_featurecatalog') THEN
                        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.table_name);
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_policies
                            WHERE schemaname = 'public'
                              AND tablename = r.table_name
                              AND policyname = 'tenant_isolation'
                        ) THEN
                            EXECUTE format(
                                $$CREATE POLICY tenant_isolation ON public.%I
                                  USING (
                                    tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::bigint
                                  )$$,
                                r.table_name
                            );
                        END IF;
                    END IF;
                END LOOP;
            END $$;
            """
        )


def reverse_postgres_tenant_guards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            DECLARE
                r RECORD;
                cname text;
            BEGIN
                FOR r IN
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = 'tenant_id'
                LOOP
                    IF r.table_name NOT IN ('tenants_tenant', 'tenants_tenantdomain', 'subscriptions_subscriptionplan', 'featureflags_featurecatalog') THEN
                        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I', r.table_name);
                        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', r.table_name);
                    END IF;
                END LOOP;

                FOR r IN
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = 'branch_id'
                      AND table_name <> 'restaurants_branch'
                LOOP
                    cname := r.table_name || '_branch_tenant_fk';
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = cname
                    ) THEN
                        EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', r.table_name, cname);
                    END IF;
                END LOOP;
            END $$;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("restaurants", "0001_initial"),
        ("subscriptions", "0001_initial"),
        ("featureflags", "0001_initial"),
        ("accounts", "0001_initial"),
        ("users", "0001_initial"),
        ("menu", "0001_initial"),
        ("orders", "0001_initial"),
        ("inventory", "0001_initial"),
        ("printing", "0001_initial"),
        ("reports", "0001_initial"),
        ("crm", "0001_initial"),
        ("hr", "0001_initial"),
        ("audit", "0001_initial"),
        ("backup", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(apply_postgres_tenant_guards, reverse_postgres_tenant_guards),
    ]
