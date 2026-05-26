# Simulink Simulation

Small repository with a MATLAB/Simulink model, helper scripts, and related data for running and analyzing simulations.

## Estrutura
- RT_LAB_SIM
- models/          # Simulink models (.slx)
- scripts/         # MATLAB scripts for setup, simulation, and analysis
- data/            # Input data or configuration files
- results/         # Simulation outputs (not tracked)
- README.md
- .gitignore
- .gitattributes

## Requisitos
- MATLAB with Simulink
- Signal Processing / Control Toolboxes as required by the models
- (Optional) RT-LAB if using RT_LAB_SIM components

## Uso rápido
1. Abra MATLAB na máquina Linux.
2. Navegue para a pasta do projeto:
   cd /home/pi/Documents/Lab_Simulation
3. Abra o modelo Simulink em models/ e execute via Simulink ou rode scripts em scripts/:
   - Ex.: abrir modelo: open('models/your_model.slx')
   - Ex.: rodar script: run('scripts/run_simulation.m')

## Boas práticas
- Versione resultados importantes em results/ ou exporte para pasta separada.
- Documente dependências de toolbox nos scripts.

## Contato
Manter documentação no repositório para facilitar reprodução.