%% Init Values

Cable_Temp = 25;

SOC0 = 0.7; % Inicial Soc


%% Tesla Model 3 Long Range - pack 96s46p aproximado

AH = 217;              % Capacidade nominal [Ah]
AH1 = 0.5 * AH;        % 50% SOC

R_SD = 1e6;            % Auto-descarga [ohm]

% Temperatura 1, por exemplo 25 °C
T1 = 25;

Vnom = 403.2;     % V, tensão máxima/nominal definida no teu modelo
V1 = 357;         % V, tensão em AH1

R0 = 0.020;       % Ohm, resistência interna a 25 °C

R_RC1 = 0.005;      % Ohm
tau1 = 30;        % s

R_RC2 = 0.010;      % Ohm
tau2 = 300;       % s


% Temperatura 2, por exemplo 0 °C
T2 = 0;

Vnom_T2 = 400;        % V, ligeiramente menor a frio
V1_T2 = 352;          % V, ligeiramente menor a frio

R0_T2 = 2.5 * R0;     % Ohm, resistência interna maior a 0 °C

R_RC1_T2 = 2.5 * R_RC1;   % Ohm
tau1_T2 = 60;         % s

R_RC2_T2 = 2.5 * R_RC2;   % Ohm
tau2_T2 = 600;        % s

