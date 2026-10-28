"""
Script interactivo para vincular y subir el repositorio a GitHub - FONOCENTER IPS.
"""
import os
import shutil
import subprocess
import sys


def get_git_executable():
    which_git = shutil.which("git")
    if which_git:
        return which_git
    
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"),
        r"C:\Program Files\Git\cmd\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "git"


def main():
    print("=" * 65)
    print("        SUBIR AUDITORIA HC FONOCENTER A GITHUB")
    print("=" * 65)
    
    git_bin = get_git_executable()
    
    # URL argument or prompt
    if len(sys.argv) > 1:
        repo_url = sys.argv[1].strip().strip('"').strip("'")
    else:
        print("\nPegue la URL completa de su repositorio de GitHub")
        print("(Ejemplo: https://github.com/tu-usuario/auditoria-fonocenter.git)")
        try:
            repo_url = input("\nURL: ").strip().strip('"').strip("'")
        except EOFError:
            repo_url = ""
    
    if not repo_url:
        print("\n[ERROR] No se especificó ninguna URL.")
        input("\nPresione Enter para salir...")
        return
        
    print(f"\n[1/3] Vinculando origen: {repo_url}...")
    subprocess.run([git_bin, "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
    subprocess.run([git_bin, "remote", "add", "origin", repo_url])
    
    print("\n[2/3] Configurando rama 'main'...")
    subprocess.run([git_bin, "branch", "-M", "main"])
    
    print("\n[3/3] Subiendo cambios a GitHub...")
    res_push = subprocess.run([git_bin, "push", "-u", "origin", "main"])
    
    if res_push.returncode == 0:
        print("\n" + "=" * 65)
        print("  ¡ÉXITO! EL PROYECTO SE HA SUBIDO CORRECTAMENTE A GITHUB.")
        print("=" * 65)
    else:
        print("\n" + "=" * 65)
        print("  [ATENCIÓN] Si GitHub le solicita credenciales:")
        print("  Ingrese su usuario y contraseña o su Personal Access Token (PAT).")
        print("=" * 65)
    
    input("\nPresione Enter para cerrar...")


if __name__ == "__main__":
    main()
