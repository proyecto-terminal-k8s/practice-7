# Práctica 7: desplegar la calculadora completa

### Propósito

Desplegar juntos el frontend, el backend y el CronJob de limpieza de logs en el
namespace `practice-7`. El backend y el Job comparten el PVC
`calculadora-logs`: cada ejecución del Job vacía `api-requests.txt` y guarda un
registro fechado en UTC. El script de monitoreo genera operaciones de suma y
muestra las solicitudes recientes y la última limpieza. Esta práctica integra
los conceptos anteriores: namespaces, Deployments, Services, ConfigMaps,
Secrets, probes, recursos, almacenamiento persistente y CronJobs.

### Archivos

- `calculadora-stack.yaml`: namespace, ConfigMap, Secret, PVC, Deployments,
  Services y CronJob.
- `monitor-limpieza.py`: genera solicitudes y muestra el estado de los logs.

## 1. Entrar al proyecto backend

Desde el directorio `practice-7`, entra al proyecto backend.

```bash
cd ../calculadora-backend
```

## 2. Construir la imagen del backend

```bash
docker build -t calculadora-backend:latest .
```

## 3. Cargar la imagen del backend en Minikube

```bash
minikube image load calculadora-backend:latest
```

## 4. Entrar al proyecto frontend

```bash
cd ../calculadora-frontend
```

## 5. Construir la imagen del frontend

```bash
docker build -t calculadora-frontend:latest .
```

## 6. Cargar la imagen del frontend en Minikube

```bash
minikube image load calculadora-frontend:latest
```

## 7. Entrar al proyecto del Job

```bash
cd ../calculadora-job
```

## 8. Construir la imagen del Job

```bash
docker build -t calculadora-job:latest .
```

## 9. Cargar la imagen del Job en Minikube

```bash
minikube image load calculadora-job:latest
```

## 10. Volver a los manifiestos

Regresa al directorio `practice-7` para continuar con los siguientes pasos.

```bash
cd ../practice-7
```

## 11. Habilitar los addons de almacenamiento

Este paso adicional configura el almacenamiento persistente de Minikube. Para
que `csi-hostpath-driver` tenga toda su funcionalidad, primero habilita
`volumesnapshots`:

```bash
minikube addons enable volumesnapshots
```

Luego habilita `csi-hostpath-driver`, que proporciona la StorageClass
`csi-hostpath-sc` usada por el PVC:

```bash
minikube addons enable csi-hostpath-driver
```

`csi-hostpath-driver` es un addon mantenido por Kubernetes. Para consultas,
contacta al proyecto minikube en [GitHub](https://github.com/kubernetes/minikube);
la lista de mantenedores está en
[OWNERS](https://github.com/kubernetes/minikube/blob/master/OWNERS).

## 12. Desplegar la aplicación

Desde `practice-7`, aplica el manifiesto integrado que crea el
namespace y todos los recursos de la práctica.

```bash
kubectl apply -f calculadora-stack.yaml
```

## 13. Esperar los Deployments

Espera hasta que el backend y el frontend estén disponibles.

```bash
kubectl rollout status deployment/calculadora-backend -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

## 14. Verificar los recursos

Comprueba que los Pods estén ejecutándose, que el PVC esté enlazado y que
existan los recursos de configuración y el CronJob.

```bash
kubectl get deployments,replicasets,pods,pvc,services,endpoints,configmaps,secrets,cronjobs -n practice-7
```

El CronJob se ejecuta cada cinco minutos, según el horario UTC
`*/5 * * * *`.
El frontend tiene dos réplicas con actualización gradual; el backend conserva
una réplica para evitar conflictos con el volumen de logs `ReadWriteOnce`.

El ConfigMap `calculadora-config` configura el host y puerto del backend para
el frontend. El Secret `calculadora-backend` proporciona
`REQUEST_LOG_FILE` al backend y al CronJob, siguiendo el ejercicio de la
Práctica 4. En este ejemplo el valor es una ruta, no un dato confidencial:
Base64 no cifra los Secrets; en producción no guardes información sensible sin
configurar cifrado y controles de acceso en el clúster.

Inspecciona la configuración y los metadatos del Secret sin revelar sus
valores:

```bash
kubectl describe configmap calculadora-config -n practice-7
```

```bash
kubectl describe secret calculadora-backend -n practice-7
```

## 15. Escalar el frontend y verificar el Service

Escala temporalmente el frontend a tres réplicas y comprueba los Pods y los
endpoints que selecciona el Service:

```bash
kubectl scale deployment/calculadora-frontend --replicas=3 -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

```bash
kubectl get deployments,pods,endpoints -n practice-7
```

Regresa a las dos réplicas definidas en el manifiesto:

```bash
kubectl scale deployment/calculadora-frontend --replicas=2 -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

## 16. Revisar el historial y probar un rollback

Cambia una variable de demostración para crear una revisión sin alterar el
funcionamiento de la aplicación:

```bash
kubectl set env deployment/calculadora-frontend PRACTICE_ROLLOUT_DEMO=revision-2 -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

```bash
kubectl rollout history deployment/calculadora-frontend -n practice-7
```

Revierte a la revisión anterior y espera a que vuelva a estar disponible:

```bash
kubectl rollout undo deployment/calculadora-frontend -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

## 17. Abrir la calculadora

Mantén el proceso abierto y visita `http://localhost:3000` en el navegador.

```bash
kubectl port-forward service/calculadora-frontend 3000:80 -n practice-7
```

## 18. Abrir el acceso al backend

En otra terminal, mantén el proceso abierto para que el script de monitoreo
pueda enviar solicitudes directamente al backend.

```bash
kubectl port-forward service/calculadora-backend 8080:8080 -n practice-7
```

## 19. Generar solicitudes y observar la limpieza

Desde `practice-7`, ejecuta el script en otra terminal. Usa
`--requests-per-interval` para indicar cuántas peticiones enviar en cada grupo
y `--interval` para establecer los segundos de pausa entre grupos:

```bash
python3 monitor-limpieza.py --requests-per-interval 10 --interval 2
```

El script seguirá enviando grupos de peticiones hasta que lo detengas con
Ctrl+C. Usa `--url` para indicar una URL de backend distinta:

```bash
python3 monitor-limpieza.py --url http://localhost:8080 --requests-per-interval 10 --interval 2
```

El script muestra las respuestas de las operaciones, las últimas líneas de
`api-requests.txt` y el registro de limpieza más reciente. Al ejecutarse el
CronJob, el archivo activo aparecerá vacío; las solicitudes posteriores
volverán a llenarlo. Pulsa Ctrl+C para detener el monitoreo.

## 20. Verificar la persistencia del PVC

Detén el monitoreo y ambos procesos de `port-forward` con Ctrl+C. Comprueba que
las solicitudes quedaron en el volumen persistente:

```bash
kubectl exec deployment/calculadora-backend -n practice-7 -- cat /app/logs/api-requests.txt
```

Elimina el Pod del backend. El Deployment lo reemplazará, pero el PVC conservará
los logs:

```bash
kubectl delete pod -l app.kubernetes.io/name=calculadora-backend -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-backend -n practice-7
```

```bash
kubectl exec deployment/calculadora-backend -n practice-7 -- cat /app/logs/api-requests.txt
```

## 21. Ejecutar manualmente el Job del CronJob

Además de la programación automática, crea una ejecución inmediata a partir
del CronJob. Elimina una ejecución anterior con el mismo nombre para poder
repetir este paso:

```bash
kubectl delete job calculadora-cleanup-manual --ignore-not-found -n practice-7
```

```bash
kubectl create job --from=cronjob/calculadora-request-logs-cleanup calculadora-cleanup-manual -n practice-7
```

```bash
kubectl wait --for=condition=complete job/calculadora-cleanup-manual --timeout=180s -n practice-7
```

## 22. Verificar los Jobs y sus logs

Lista las ejecuciones del CronJob y consulta los logs del Job manual:

```bash
kubectl get cronjobs,jobs -n practice-7
```

```bash
kubectl logs job/calculadora-cleanup-manual -n practice-7
```

```bash
kubectl get pods,pvc -n practice-7
```

El Job vacía `api-requests.txt` y crea en el PVC un archivo
`api-requests-cleanup-YYYY-MM-DD.txt` con la fecha UTC. El backend puede seguir
escribiendo solicitudes nuevas después de la limpieza.

## 23. Limpiar la práctica

Elimina el namespace y todos los recursos asociados.

```bash
kubectl delete namespace practice-7
```
